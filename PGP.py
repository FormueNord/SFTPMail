from gnupg import GPG
import os
import typing

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
    def __init__(self,  recipient_fp: str, sign_fp: str = None, gpghome : str = "GnuPG", gpgexe : str = None, gpg_encoding : str = "utf-8"):
        # bound to obj so that user can change the recipient or sign fp property
        self.recipient_fp = recipient_fp
        self.sign_fp = sign_fp
        
        if gpgexe is None:
            gpgexe = os.path.join(gpghome,"bin","gpg.exe")
        
        
        self.GPG = GPG(
            gpgbinary = gpgexe,
            gnupghome = gpghome)
        self.GPG.encoding = "utf-8"



    def encrypt(self,file_path: str, always_trust: bool = True, save_file: bool = False, **kwargs) -> str:
        """
        Encrypts the specified file with using the public key matching self.recipient_fp 
        
        INPUT:
            file_path (str): path to the file to be encrypted
            always_trust  (bool): trust the key matching self.recipient_fp?
            save_file (bool): if true file is saved with suffix .encrypted
            **kwargs: any kwargs is supplied to gnupg.GPG.encrypt_file()
        
        RETURNS:
            file's encrypted content as a string
        """
        with open(file_path, "rb") as f:
            encr_result = self.GPG.encrypt_file(
                file = f,
                recipients = self.recipient_fp,
                sign = self.sign_fp,
                always_trust = always_trust,
                **kwargs
            )
        
        if not(encr_result.ok):
            raise Exception(f"File: {file_path} was not encrypted correctly with error {encr_result.__dict__['status']}")

        content = encr_result.data.decode(self.GPG.encoding)
        # remove any carriage return
        content = content.replace("\r","")

        if save_file:
            with open(file_path + ".encrypted","w") as f:
                f.write(content)

        return content

    def decrypt(self, file_path, always_trust = True, save_file = False, **kwargs) -> str:
        """
        Decrypts the specified file with using stored private keys
        
        INPUT:
            file_path (str): path to the file to be encrypted
            always_trust  (bool): trust the key matching self.recipient_fp?
            save_file (bool): if true file is saved with suffix .encrypted
            **kwargs: any kwargs is supplied to gnupg.GPG.decrypt_file()
        
        RETURNS:
            file's decrypted content as a string | if file wasn't encrypted to begin with the file's content as a string
        """

        with open(file_path, "rb") as f:

            if  b'-----BEGIN PGP MESSAGE-----\r\n' not in f.readlines():
                print("It does not look as if the file is PGP encrypted")
                print("Returns the file content without decryption and without saving file if specified")
                f.seek(0,0)
                return f.read().decode(self.GPG.encoding)

            
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
            with open(file_path + "test", "w") as f:
                f.write(content)

        return content
        

    def add_new_local_key(self, paths: typing.Union[list[str], str]):
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
            with open(path,'r') as f:
                key = f.read()
                import_result = self.GPG.import_keys(key)
            import_results.append(import_result)
        return import_result

