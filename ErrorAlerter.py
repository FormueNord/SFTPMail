import os
from email.mime.text import MIMEText
from smtplib import SMTP
import ast

class ErrorAlerter():
    
    _cred_file_name = "\\".join(__file__.split("\\")[0:-1]) + "\\mail_cred_details.txt"

    def __init__(self,receivers: str, subject: str, warning_text: str):
        self.receivers = receivers
        self.warning_text = warning_text
        self._load_credentials()
        self.subject = subject

    def _load_credentials(self):
        #create new file if none is available
        if not os.path.isfile(self._cred_file_name):
            print("No mail_cred_details.txt file found in root")
            self._create_new_credentials_file()
        with open(self._cred_file_name,"r") as f:
            content = f.read()
            content_str = bytes.fromhex(content).decode("UTF-8")
            content_dict = ast.literal_eval(content_str)
            self.uid, self.pwd = content_dict["uid"], content_dict["pwd"]
            # fails and raises error if uid and pwd can't authenticate
            self._login_test(self.uid, self.pwd)
        print("read the ErrorAlert's credentials file!")
        return

    def _create_new_credentials_file(self):
        print("If you wanna create a new file, it has to be a microsoft mail, otherwise code needs changes")
        create_new = input("Do you wanna create a new credentials file? (Y/N):  ")
        if create_new:
            uid = input("Whats your mail adress?:  ")
            pwd = input("Whats your password?:   ")

            # fails and raises error if uid and pwd can't authenticate
            self._login_test(uid,pwd)

            creds = {"uid":uid,"pwd":pwd}
            with open(self._cred_file_name,"w") as f:
                f.write(str(creds).encode("UTF-8").hex())
            
            print("New credentials file created!")
        else: 
            print("An error will be raised since no credentials are available")
        return

    def error_alert(self):
        self._setup_email()
        self._send_email()

    def _setup_email(self):
        self.receivers = self.receivers.split(',')
        message = MIMEText(str(self.warning_text))
        message['subject'] = self.subject
        message['From'] = self.uid
        message['To'] = self.receivers[0]
        message['Cc'] = ';'.join(self.receivers[1:])
        self.message = message
        return 

    @staticmethod
    def _login_test(uid, pwd):
        try:
            with SMTP('smtp.office365.com',587) as server:
                server.ehlo()
                server.starttls()
                server.login(uid,pwd)
        except Exception as e:
            raise Exception(f"Failed to authenticate using the credentials error code is: {e}")

    def _send_email(self):
        with SMTP('smtp.office365.com',587) as server:
            server.ehlo()
            server.starttls()
            server.login(self.uid,self.pwd)
            server.sendmail(self.uid,self.receivers,self.message.as_string()) 
        return