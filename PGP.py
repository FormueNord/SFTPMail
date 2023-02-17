from gnupg import GPG
import os
from typing import Union

class PGP:
    """
        A wrapper for the gnupg.GPG module making decryption and encryption cleaner and more user friendly.

        gnupg has been tested with GnuPG 1.4.9, and a binary version of the software is required to run this wrapper.
        for more info looks towards: https://gnupg.readthedocs.io/en/latest/
        Per default this module will use a GnuPG folder in the working directory and GnuPG\bin\gpg.exe for path to the binary
    
    INPUT:
        connection_properties (dict[str]): contains the connection properties. Content will be passed on the pysftp.Connection.
            OBLIGATORY:
                recipient_fp (str): Fingerprint of the public key to used for encryption/decryption (can be changed after instantiation)
            OPTIONAL:
                sign_fp (str): fingerprint of the private key used to sign the encryption
                gpghome (str) = 'GnuPG': path to the GnuPG folder
                gpgexe (str) = gpghome\bin\gpg.exe: Your password at the remote machine
                gpg_encoding (str) = 'utf-8': file encoding

    ATTRIBUTES:
        recipient_fp (str): fingerprint of the recipients public key
        sign_fp (str): fingerprint of the private key used to sign any encryption
        GPG (GPG): instance of gnupg.GPG instantiated with specified gpgexe and gpghome
    
    """

    # make sure default_comment is defined for method add_comment default arg
    default_comment = None

    message_beginning_indicator = "-----BEGIN PGP MESSAGE-----"
    
    def __init__(self,  recipient_fp: str, sign_fp: str = None, gpghome : str = "GnuPG", gpgexe : str = None, 
                gpg_encoding : str = "utf-8", default_comment : Union[str, list[str]] = None):
        # bound to obj so that user can change the recipient or sign fp property
        self.recipient_fp = recipient_fp
        self.sign_fp = sign_fp
        self.default_comment = default_comment

        if gpgexe is None:
            gpgexe = os.path.join(gpghome,"bin","gpg.exe")
        
        self.GPG = GPG(
            gpgbinary = gpgexe,
            gnupghome = gpghome)
        self.GPG.encoding = gpg_encoding



    def encrypt(self, file_path: Union[str, list[str]], always_trust: bool = True, save_file: bool = False, add_default_comment = True, **kwargs) -> list[str]:
        """
        Encrypts the files specified in a list of paths using the public key matching self.recipient_fp 
        
        ARGS:
            file_path (list[str] | str): path to the file to be encrypted

        
        KWARGS:
            always_trust (bool): trust the key matching self.recipient_fp?
            save_file (bool): if true file is saved with suffix .encrypted
            add_default_comment (bool): if true default comment is added to the content. self.default_comment must be specified.
            **kwargs: any kwargs is supplied to gnupg.GPG.encrypt_file()
        
        RETURNS:
            list with the encrypted content as strings for each item
        """

        if isinstance(file_path,str):
            file_path = [file_path]

        content_holder = []
        for path in file_path:
            with open(path, "rb") as f:
                encr_result = self.GPG.encrypt_file(
                    file = f,
                    recipients = self.recipient_fp,
                    sign = self.sign_fp,
                    always_trust = always_trust,
                    **kwargs
                )
            
            if not(encr_result.ok):
                raise Exception(f"File: {path} was not encrypted correctly with error {encr_result.__dict__['status']}")

            content = encr_result.data.decode(self.GPG.encoding)

            # remove any carriage return
            # if this is deleted it creates double linespaces
            content = content.replace("\r","") 

            if add_default_comment and self.default_comment != None:
                content = self.add_comment(content)

            if save_file:
                path += ".encrypted"
                with open(path,"w") as f:
                    f.write(content)
                 
            content_holder.append(content)
        return content_holder

    def decrypt(self, file_path, always_trust = True, save_file = False, **kwargs) -> list[str]:
        """
        Decrypts the files specified in a list of paths using stored private keys
        
        INPUT:
            file_path (str): path to the file to be encrypted
            always_trust  (bool): trust the key matching self.recipient_fp?
            save_file (bool): if true file is saved with suffix .encrypted
            **kwargs: any kwargs is supplied to gnupg.GPG.decrypt_file()
        
        RETURNS:
            list with the decrypted content as strings for each item
        """

        if isinstance(file_path, str):
            file_path = [file_path]

        content_holder = []
        for path in file_path:
            with open(path, "r") as f:
                # check if file is encrypted
                if  self.message_beginning_indicator not in f.readlines():
                    print("It does not look as if the file is PGP encrypted")
                    print("Returns the file content without decryption and without saving file if specified")
                    f.seek(0,0)
                    content_holder.append(f.read())
                    continue

                f.seek(0,0)
                decrypted = self.GPG.decrypt_file(
                    file = f,
                    always_trust = always_trust,
                    **kwargs
                )
            
            if not decrypted.ok:
                raise Exception(f"File: {file_path} was not decrypted correctly with error message {decrypted.__dict__['status']}")

            content = decrypted.data.decode(self.GPG.encoding)
            
            if save_file:
                with open(path, "w") as f:
                    f.write(content)
                
            content_holder.append(content)
        return content_holder

    def add_comment(self, content : str, comments : Union[str,list[str]] = default_comment) -> str:
        """
        Adds a comment(s) to the content arg
        comments are added on the line after self.message_beginning_indicator string (default is -----BEGIN PGP MESSAGE-----)
        Comments are written as:
            'Comment: {you comment} \n'
        
        ARGS:
            content (str): String line seperated with \n
            comments (str | list[str]): the comment(s) to insert. Default is the self.default_comment attribute
        
        RETURNS:
            supplied content string with comments added
        """
        # ensure instance value is used as default if comments == None
        if comments == PGP.default_comment:
            comments = self.default_comment

        if isinstance(comments, str):
            comments = [comments]

        row_after_message_begin = None
        content = content.split("\n")
        for i,row in enumerate(content):
            if self.message_beginning_indicator in row:
                row_after_message_begin = i + 1
                break
        
        for comment in comments:
            comment = f"Comment: {comment}"
            content.insert(row_after_message_begin, comment)

        content = "\n".join(content)
        return content
        

    def add_new_local_key(self, paths: Union[list[str], str]):
        """
        Adds a new key to the GNUPG keyring at the self.gpghome location (location is set on instantiation)

        INPUT:
            paths (list[str] | str): path(s) to the key(s)

        RETURNS:
            Fingerprint(s) of the added key(s)
        """
        # Eksempel på hvordan man importere krypteringsnøgler

        if isinstance(paths,str):
            paths = [paths]

        import_results = []
        for path in paths:
            with open(path,'rb') as f:
                key = f.read()
                import_result = self.GPG.import_keys(key)
            import_results.append(import_result)
        return import_result

if __name__ == "__main__":
    import gnupg
    print(gnupg.__version__)