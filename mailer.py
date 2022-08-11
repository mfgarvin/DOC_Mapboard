import yagmail

file = open("secure/mail_secrets.txt", "r")
username = file.readline()
password = file.readline()
to = file.readline()

yag = yagmail.SMTP(username, password)

def sendmail(subject, body):
	yag.send(to, subject, body)
#subject = "Hello there!"

#contents = ['Hey there! \n This is the body of my email, and here is the text. ']

#yag.send(to, subject, contents)

#yag = yagmail.SMTP('mygmailusername', 'mygmailpassword')
#contents = ['This is the body, and here is just text http://somedomain/image.png',
#            'You can find an audio file attached.', '/local/path/song.mp3']
#yag.send('to@someone.com', 'subject', contents)
