from pysftp import Connection, CnOpts
from typing import Callable
import os

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

    def __init__(self, connection_properties: dict[str]):
        self._check_if_setup()
        self.connection_properties = self._connection_properties_check(connection_properties)
    

    def _connection_properties_check(connection_properties):

        # removes need for user to import pysftp.CnOpts
        if "cnopts" in connection_properties.keys():
            try:
                connection_properties["cnopts"] = CnOpts(connection_properties["cnopts"])
            except Exception as e:
                raise(f"Failed to instantiate CnOpts obj with the specified cnopts parameter. The error was {e}")
        return connection_properties
    

    def _open_connection_decorator(connection_call_back: Callable, **kwargs):
        """
        Decorator to execute Callable within the context of the SFTP connection
        """
        def _open_connection(self):
            with Connection(**self.connection_properties) as sftp:
                connection_call_back(sftp, **kwargs)
        return _open_connection


    @_open_connection_decorator
    def send_to(self,sftp: Connection, remote_path: str):
        """
        Sends all files in the Outbox folder to the specified remote_path using SFTP.
        Prior to being sent files are placed in the Awaiting folder.

        INPUT:
            remote_path (str): path to the remote destination
        """
        # get relative path to files
        files = os.listdir("Outbox")
        for file in files:
            outbox_path = os.join("Outbox",file)
            awaiting_path = os.join("Awaiting",file)
            # File is moved to make sure failed file deliveries don't clog up the system
            # Or make sure the same file can't mistakently be sent twice
            os.rename(outbox_path,awaiting_path)

            # Copy file to remote destination
            remote_path = os.join(remote_path,file)
            sftp.put(awaiting_path,remote_path)
            
            # Move file to sent
            sent_path = os.join("Sent",file)
            os.rename(awaiting_path,sent_path)


    @_open_connection_decorator
    def receive_from(self, sftp: Connection, remote_path: str):
        """
        Fetch all files on the remote path and place them into the local Inbox folder

        INPUT:
            remote_path (str): path to the remote destination from which files are fetched
        """
        remote_files = sftp.listdir(remote_path)
        for file_name in remote_files:
            remote_file_path = os.join(remote_path, file_name)
            # make sure a unique name is given to the file
            local_path = self._non_conflicting_name("Inbox",file_name)
            sftp.get(remote_file_path,local_path, preserve_mtime = True)
            sftp.remove(remote_path)


    def _non_conflicting_name(self, local_path: str, file_name: str, iterator = 0):
        """
        Check if the filename already exists within the local folder.
        If there's a conflict add _x (where x is a number) to make a non-conflicting file name

        INPUT:
            local_path (str): relative local path to a folder
            file_name (str): name of the file

        RETURNS:
            (str) non-conflicting filename
        """
        file_path = os.join(local_path, file_name)
        if os.path.exists(file_path):
            iterator += 1

            # add _x as suffix to the file name
            file_name = file_name.split(".")
            file_name[0] = file_name[0] + "_" + str(iterator)
            file_name = ".".join(file_name)

            # recurse until a non-conflicting name is found
            file_path = self._new_file_name(local_path, file_name, iterator = iterator)
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