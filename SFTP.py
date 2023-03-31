from pysftp import Connection, CnOpts
from typing import Callable, Union
from SFTPMail import PGP
import os
import shutil

class SFTPDecor:
    @classmethod
    def _open_connection_decorator(self, func: Callable):
        """
        Decorator to execute Callable within the context of the SFTP connection
        """
        def _open_connection(*args, **kwargs):
            with Connection(**args[0].connection_properties) as sftp:
                return func(*args, sftp = sftp, **kwargs)
        return _open_connection

class SFTP:
    """
    Represents a SFTP connection with methods to do basic communication using SFTP
    
    INPUT:
        connection_properties (dict[str]): contains the connection properties. Content will be passed on the pysftp.Connection.
            OBLIGATORY:
                host (str): The hostname or IP of the remote machine
            OPTIONAL:
                username (str): Your username at the remote machine
                private_key (str): path to the private key file or paramiko.AgentKey
                password (str): Your password at the remote machine
                port (str) *Default 22*: The SSH port of the remote machine
                private_key_pass (str): password to use, if private_key is encrypted
                cnopts (str): path to a readable file containing information on known hosts
                default_path (str): set a default path upon connection

    ATTRIBUTES:
        connection_properties (dict[str]): contains the connection properties. 
            If cnopts is specified its made into an instance of CnOpts
    """

    # defines the paths required to run the class.
    # if missing these paths will be created in the working directory
    required_paths = ["Inbox","Outbox","Sent","Awaiting"]

    def __init__(self, connection_properties: dict[str], pgp : PGP = None):
        self._check_if_setup()
        self.connection_properties = self._connection_properties_check(connection_properties)
        self.pgp = pgp



    def _connection_properties_check(self, connection_properties):
        if "host" not in connection_properties.keys():
            raise ValueError("Excepted a value for host in connection_properties")

        # removes need for user to import pysftp.CnOpts
        if "cnopts" in connection_properties.keys():
            try:
                connection_properties["cnopts"] = CnOpts(connection_properties["cnopts"])
            except Exception as e:
                raise(f"Failed to instantiate CnOpts obj with the specified cnopts parameter. The error was {e}")
        else:
            # https://stackoverflow.com/questions/38939454/verify-host-key-with-pysftp
            print("It is advised to add a cnopts parameter to check for known host. Current connection is susceptible to man-in-the-middle attacks")
            cnopts = CnOpts()
            cnopts.hostkeys = None
            print("cnopts.hostkeys has been set to = None")
            connection_properties["cnopts"] = cnopts

        return connection_properties    

    def _PGP(self, file_paths: Union[str,list[str]], encrypt_or_decrypt: str, **kwargs) -> list[str]:
        """
        PGP en/decrypts the file at file_path using the PGP object passed to SFTP, saves the file and returns output path.
        output path if encrypt_or_decrypt = "encrypt" is Outbox\file_name
        output path if encrypt_or_decrypt = "decrypt" is Inbox\file_name

        ARGS:
            file_path (str | list[str]): path(s) to file(s)
            encrypt_or_decrypt (str): "encrypt" or "decrypt"

        RETURNS:
            list of output paths for created encrypted file
        """

        if self.pgp == None:
            raise Exception("The SFTP obj must have an assigned pgp value. Can be assigned during initialization.")
        
        if isinstance(file_paths,str):
            file_paths = [file_paths]

        file_names = [os.path.basename(file_path) for file_path in file_paths]
        
        if encrypt_or_decrypt.lower() == "encrypt":
            file_content = self.pgp.encrypt(file_paths) 
            file_output_paths = [self._non_conflicting_name("Outbox",file_name) for file_name in file_names]   
        elif encrypt_or_decrypt.lower() == "decrypt":
            file_content = self.pgp.decrypt(file_paths)
            file_output_paths = [self._non_conflicting_name("Inbox",file_name) for file_name in file_names]
        
        for content, path in zip(file_content, file_output_paths):
            with open(path, "w") as f:
                f.write(content)
        return file_output_paths

    def _no_cryption(self, file_paths: Union[str,list[str]], encrypt_or_decrypt, **kwargs) -> list[str]:
        """
        Applies encryption to files and simply copies them to the Inbox/Outbox for further processing. Returns output path.
        output path if encrypt_or_decrypt = "encrypt" is Outbox\\file_name
        output path if encrypt_or_decrypt = "decrypt" is Inbox\\file_name

        ARGS:
            file_path (str | list[str]): path(s) to file(s)
            encrypt_or_decrypt (str): "encrypt" or "decrypt"

        RETURNS:
            output path for file
        """
        if isinstance(file_paths, str):
            file_paths = [file_paths]

        if encrypt_or_decrypt.lower() == "encrypt":
            dst_folder = "Outbox"
        elif encrypt_or_decrypt.lower() == "decrypt":
            dst_folder = "Inbox"
        file_names = [os.path.basename(file_path) for file_path in file_paths]
        file_output_paths = [self._non_conflicting_name(dst_folder,file_name) for file_name in file_names]

        for src,dst in zip(file_paths,file_output_paths):
            shutil.copy2(src,dst)
        return file_output_paths
    
    cryption_methods = {"None":_no_cryption, "PGP": _PGP}

    @SFTPDecor._open_connection_decorator
    def send_to(self, remote_dst: str, cryption_method: str = "None", **kwargs) -> None:
        """
        Sends all files in the Outbox folder to the specified remote_path using SFTP.
        Prior to being sent files are placed in the Awaiting folder.

        INPUT:
            remote_dst (str): path to the remote destination
        """
        # get the sftp Connection passed from _open_connection_decorator as a kwarg
        sftp = kwargs.pop("sftp")

        # get relative path to files
        file_names = os.listdir("Outbox")

        for file_name in file_names:
            outbox_path = os.path.join("Outbox",file_name)
            awaiting_path = self._non_conflicting_name("Awaiting",file_name)
            # make sure the same file can't mistakently be sent twice
            os.rename(outbox_path,awaiting_path)
            remote_path = os.path.join(remote_dst,file_name)
            
            # make sure exception can run and the wanted Exception is reached
            file_to_send_path = ["temp"]

            # If the system fails put the file from awaiting back into the Outbox before throwing an error
            try:
                # apply selected encryption method to file and return path of encrypted file
                file_to_send_path = self.cryption_methods[cryption_method](self, awaiting_path, "encrypt")
                assert len(file_to_send_path) == 1
                # make list[str] into str (should only contain one item)
                file_to_send_path = file_to_send_path[0]
                # Copy file to remote destination
                sftp.put(file_to_send_path,remote_path)
            except Exception as e:
                # is run if self.cryption_methods fail in the above
                if file_to_send_path[0] == "temp":
                    os.rename(awaiting_path, outbox_path)
                    raise Exception(f"Encryption failed, error code was: {e}")
                
                # clean created files (if any) and move awaiting back to outbox before failing
                if file_to_send_path[0] != awaiting_path and os.path.isfile(file_to_send_path[0]):
                    os.remove(file_to_send_path)
                os.rename(awaiting_path, outbox_path)
                raise Exception(f"Failed to put file {file_name} on the server. The error was {e}")
            
            # make sure any created encrypted file is deleted
            if os.path.isfile(file_to_send_path):
                os.remove(file_to_send_path)
            
            # Move file to sent
            sent_path = self._non_conflicting_name("Sent",file_name)
            os.rename(awaiting_path,sent_path)


    @SFTPDecor._open_connection_decorator
    def receive_from(self, remote_path: str, cryption_method: str = "None", **kwargs) -> list[str]:
        """
        Fetch all files on the remote path and place them into the local Inbox folder

        INPUT:
            remote_path (str): path to the remote destination from which files are fetched
        RETURNS:
            list of local paths to the files fetched from the server
        """
        # get the sftp Connection passed from _open_connection_decorator as a kwarg
        sftp = kwargs.pop("sftp")

        fetched_files = []
        remote_files = sftp.listdir(remote_path)
        for file_name in remote_files:
            remote_file_path = os.path.join(remote_path, file_name)
            # make sure a unique name is given to the file
            local_path = self._non_conflicting_name("Awaiting",file_name)
            sftp.get(remote_file_path,local_path, preserve_mtime = True)
            fetched_files.append(local_path)
            sftp.remove(remote_file_path)

        # path to decrypted files. Files are created in or copied to Inbox directory
        decrypted_fetched_files = self.cryption_methods[cryption_method](self, fetched_files, "decrypt")

        # remove encrypted fetched files in awaiting
        [os.remove(fetched_file) for fetched_file in fetched_files]

        return decrypted_fetched_files

    def test_connection(self) -> dict:

        @SFTPDecor._open_connection_decorator
        def test_func(*args, **kwargs):
            return
        
        result = {"OK":True, "Exception":None}

        try:
            test_func(self)
            return result
        except Exception as e:
            result["Exception"] = e
            result["OK"] = False
            return result


    def _non_conflicting_name(self, destination_path: str, file_name: str) -> str:
        """
        Check if the filename already exists within the local folder.
        If there's a conflict add _x (where x is a number) to make a non-conflicting file name

        INPUT:
            destination_path (str): relative local path to a folder
            file_name (str): name of the file

        RETURNS:
            (str) non-conflicting filename
        """
        file_path = os.path.join(destination_path, file_name)
        iterator = 0
        while os.path.exists(file_path):
            iterator += 1

            # add '_x' as suffix to the file name
            file_path_split = file_path.split(".")
            file_path_split[0] = file_path_split[0] + "_" + str(iterator)
            file_path_try = ".".join(file_path_split)

            # check if new file path exists
            if not os.path.exists(file_path_try):
                file_path = file_path_try
                break
            
        return file_path


    def _check_if_setup(self):
        """
        Check if the current working directory contains the required paths
        """
        files_in_dir = os.listdir()
        paths_in_folder = []
        for path in self.required_paths:
            paths_in_folder.append(path in files_in_dir)

        if not all(paths_in_folder):
            print("It seems as if you are missing some of the required paths.")
            user_response = self._prompt_new_setup()
            if not user_response:
                return
            paths_missing = self._find_missing_paths(paths_in_folder)
            self._setup(paths_missing = paths_missing, no_warning = True)

        return True


    def _prompt_new_setup(self):
        """
        Prompts if the user wishes to make a new setup

        Returns:
            Boolean with value True if user says yes to a new setup
        """
        print(f"""
            The current working directory was found to be missing some of the required folders.
            If current paths exists, and they contain any important information, you should as a precaution move these files to a path outside the working directory""")
        response = input("Do you wish to make a new setup? (Y/N): ")
        
        if response.lower() != "y":
            print("Setup was not run and the SFTP class is shutting down")
            return False
        return True
    

    def _find_missing_paths(self,paths_in_folder: list[str]) -> list[str]:
        """
        Check if the paths_in_folder arg contains the required strings.

        INPUT:
            paths_in_folder (list[str]): contains the files/folders in the current working directory. 
            Relative paths from current working directory.

        RETURNS:
            list[str]: required relative paths missing in the current working directory
        """
        paths_missing = []
        for path, path_in_folder in zip(self.required_paths, paths_in_folder):
            if not path_in_folder:
                paths_missing.append(path)
        return paths_missing


    def _setup(self, paths_missing: list[str] = False, no_warning = False):
        """
        Creates the paths in the paths_missing arg

        INPUT:
            paths_missing (list[str]): the relative paths missing from the current working directory
            no_warning (bool) = False: if False the caller will be warned and prompted for whether they want to run the setup
        """
        if not no_warning:
            print("You are about to make a new setup. Any files within the current working directory could potentially be compromised.")
            response = input("Are you sure that you wish to do this? (Y/N): ")
            if response.lower() != "y":
                print("Setup was not run")
                return

        # If paths_missing is default value False all the paths should be regarded as missing
        if paths_missing == False:
            paths_missing = self.required_paths

        # Find names of the missing folders - might want to setup other stuff than only folders in the future
        folders_missing = [folder_missing for folder_missing in paths_missing if "." not in folder_missing]
        for folder_missing in folders_missing:
            try:
                os.makedirs(folder_missing)
            except FileExistsError:
                print(f"{folder_missing} folder not created since it already exists")
            
        print("Finished setting things up")

