import pytest
import os
from io import StringIO
import shutil




import mock
class fake_Connection:

        def __init__(*args, **kwargs):
            return
        
        def __enter__():
            print("Entering connection")
        
        def __exit__():
            print("Exiting connection")

        def listdir(self):
            return os.listdir(r"tests\test_files")

        def get(self, remote_file_path, local_path):
            shutil.copy2(remote_file_path,local_path)

        def remove(self, path):
            return

mock.patch("SFTP.Connection",fake_Connection).start()

from SFTPMail import SFTP




connection_properties = {"host":"abcdefg.000.000.000"}


sftp = SFTP(connection_properties)
sftp.receive_from("does not matter")
print("stop")
def clean_setup():
    """
    Cleans up the files from the SFTP class in the working directory
    """
    paths_in_dir = os.listdir()
    setupped_paths = SFTP.required_paths

    for path in setupped_paths:
        if path in paths_in_dir:
            if len(path.split(".")) > 1:
                os.remove(path)
            else:
                os.rmdir(path)


def make_setup(monkeypatch):
    """
    Function to setup the neccessary files for the SFTP class in the working directory
    """
    response = StringIO("y")
    monkeypatch.setattr("sys.stdin",response)
    sftp = SFTP(connection_properties)
    return sftp


def test_setup_yes(monkeypatch):
    """
    Test whether the needed paths are created if user says yes
    """
    make_setup(monkeypatch)

    setupped_paths = SFTP.required_paths
    paths_in_dir = os.listdir()

    # setup no longer needed so clean asap
    clean_setup()
    for path in setupped_paths:
        if path not in paths_in_dir:
            assert False, f"The path {path} which was required to be set up is missing from the working directory"

def test_setup_no(monkeypatch):
    """
    Test whether the needed paths are NOT created if the user says no
    """
    response = StringIO("n")
    monkeypatch.setattr("sys.stdin",response)
    before_setup = os.listdir()
    sftp = SFTP(connection_properties)
    after_setup = os.listdir()

    assert before_setup == after_setup, "Setup was denied and the content of the working directory should not have been changed, but it has"

def test_setup_already_exists(monkeypatch):
    """
    Test if _check_if_setup indicates that the setup is already in place
    """
    sftp = make_setup(monkeypatch)
    is_already_setup = sftp._check_if_setup()
    clean_setup()
    assert is_already_setup




# use to test SFTP.receive_from and SFTP.send_to using a mocker 
# I haven't had success with it yet 
# # https://opensource.com/article/21/9/unit-test-python
def to_test_network_dependent_calls():
    class fake_Connection:

        def __init__(*args, **kwargs):
            return
        
        def __enter__():
            print("Entering connection")
        
        def __exit__():
            print("Exiting connection")

        def listdir(self):
            return os.listdir(r"tests\test_files")

        def get(self, remote_file_path, local_path):
            shutil.copy2(remote_file_path,local_path)

        def remove(self, path):
            return


    def decorator(func):
        def wrapper(*args, **kwargs):
            with fake_Connection(**args[0].connection_properties) as sftp:
                func(*args, sftp = sftp, **kwargs)
        return wrapper