import yagmail

file = open("secure/mail_secrets.txt", "r")
username = file.readline()
password = file.readline()
to = file.readline()

yag = yagmail.SMTP(username, password)

def sendmail(subject, body):
	yag.send(to, subject, body)
