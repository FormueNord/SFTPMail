import pytest
from SFTPMail import PGP
from mock import patch
import os

test_files_folder_path = r"tests\test_files"
test_file_path = os.path.join(test_files_folder_path,"file.txt")
new_test_file_path = os.path.join(test_files_folder_path, "file_temp.txt")

def read_test_file():
    with open(test_file_path, "r") as f:
        test_file_content = f.read()
    return test_file_content

test_file_content = read_test_file()

def delete_new_files(files_prior_to_run):
    for file in os.listdir(test_files_folder_path):
        if file not in files_prior_to_run:
            os.remove(os.path.join(test_files_folder_path, file))


"""
FakeGPG and FakeResult is a fake version of the GPG class used in PGP.
These objs are patched/replaced for testing purposes.
"""

class FakeResult:
    ok = True
    data = b"abcdefghijklmnopqrstuvxyz"
    status = "foo"

    def __init__(self,data):
        self.data = data

class FakeGPG:

    encoding = "utf-8"

    def __init__(self, *args,**kwargs):
        return
    
    def encrypt_file(self, *args, **kwargs):
        return FakeResult(read_test_file().encode(self.encoding))

    
    def decrypt_file(self, *args, **kwargs):
        return FakeResult(read_test_file().encode(self.encoding))


def fake__init__(self,recipient_fp, *args, **kwargs):
    """
    Fake __init__ used to patch the PGP class
    """
    self.recipient_fp = recipient_fp
    self.sign_fp = None

    self.GPG = FakeGPG()


def test_encrypt_file(mocker):
    """
    Tests whether the file content is anyhow altered by the encrypt_file method
    """
    mocker.patch.object(PGP,"__init__",fake__init__)

    gpg = PGP("adfijaodf")
    result = gpg.encrypt(test_file_path)
    assert result == test_file_content


def test_encrypt_file_save(mocker):
    """
    Tests whether the file content is anyhow altered by the encrypt_file method with kwarg save_file = True
    """
    
    # see files prior to test runs and delete any new files in the folder at the end
    files_prior_to_run = os.listdir(test_files_folder_path)
    
    mocker.patch.object(PGP,"__init__",fake__init__)
    



    gpg = PGP("adfijaodf")
    result = gpg.encrypt(test_file_path,save_file = True)

    delete_new_files(files_prior_to_run)
    assert result == test_file_content


def test_decrypt_file(mocker):
    """
    Tests whether the file content is anyhow altered by the decrypt_file method
    """
    mocker.patch.object(PGP,"__init__",fake__init__)

    gpg = PGP("adfijaodf")
    result = gpg.decrypt(test_file_path)
    assert result == test_file_content

def test_decrypt_file_save(mocker):
    """
    Tests whether the file content is anyhow altered by the decrypt_file method with kwarg save_file = True
    """

    # see files prior to test runs and delete any new files in the folder at the end
    files_prior_to_run = os.listdir(test_files_folder_path)

    mocker.patch.object(PGP,"__init__",fake__init__)

    gpg = PGP("adfijaodf")
    result = gpg.decrypt(test_file_path, save_file = True)

    delete_new_files(files_prior_to_run)

    assert result == test_file_content


# deletes any files created in the folder by the tests






