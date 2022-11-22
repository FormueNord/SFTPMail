from pysftp import Connection, CnOpts
import os

class SFTP:
    
    required_paths = ["Inbox","Outbox","Sent"]

    def __init__(self, host: str, username: str, SSH_private_path: str, knownhosts_path: str):
        self._check_if_setup()
        self.host = host
        self.username = username
        self.SSH_private_path = SSH_private_path
        #self.knownhosts = CnOpts(knownhosts_path)

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