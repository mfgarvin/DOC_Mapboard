#! /bin/python

#Things we need to import go here:
import json
import datetime
import time
from datetime import timedelta

#Variables we need to set go here:
JSON_LOCATION="./demo.json"
LED_ALLOCATION="./leds.txt"
PARISH_ID="./ids.txt"
DAYS=["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKDAYS=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKEND=["Saturday", "Sunday"]
ledStatus = {}
#Functions? *Raises hand*
def ingest():
	readfile = open(JSON_LOCATION, "r")
	global rawjson
	rawjson = json.loads(readfile.read())

#This'll start breaking down the JSON into smaller chunks by day, as needed
def digest():
	ramjson = rawjson.copy() #Want to work on this in RAM, rather than reading from the disk every time
	global masstime_database, confession_database, adoration_database
	db1 = {}
	db2 = {}
	db3 = {}
	masstime_database = {}
	confession_database = {}
	adoration_database = {}
	try:
		for parish in allocation.copy():
#								parishName = parish[0]
			for day in DAYS: # Mass Times
				db1[day] = rawjson[parish[0]]['Mass Times'][day]
			masstime_database[parish[0]] = db1
			db1 = {}
			for day in DAYS: # Confession Times
				db2[day] = rawjson[parish[0]]['Confessions'][day]
			confession_database[parish[0]] = db2
			db2 = {}
			DAYS.append("is24hr")
			for day in DAYS: # Adoration Times
				db3[day] = rawjson[parish[0]]['Eucharistic Adoration'][day]
			adoration_database[parish[0]] = db3
			db3 = {}
			DAYS.remove("is24hr")
	except KeyError as e:
		if str(e) == "0":
			print("Out of parishes, continuing...")
			pass
		else:
			raise
	finally:
		pass

#Combining Parish Name, ID, and LED Allocation into one dictionary
def setID():
	global allocation, leddict, iddict
	#creating a 2D array for the following data
	rows, cols = (200, 3)
	allocation = [[0 for i in range(cols)] for j in range(rows)]
	leddict = json.loads(open(LED_ALLOCATION, "r").read())
	iddict = json.loads(open(PARISH_ID, "r").read())
	for key, id in iddict.items(): 		# key = parish name
		allocation[id - 1][0] = key
		allocation[id - 1][1] = id
		allocation[id - 1][2] = leddict.get(key) #LED Assignment

def chronos():
	#Take an ID from the allocation variable, check it against the different databses. - DONE
	#must be specific by weekday - DONE
	#If scheduled to be active, call the display() function. - DONE
	#format should be something like: ID, State/color, duration. - DONE
	#Add Logic to priortize status (probably should just use ifelse statements). - DONE
	#will need to either be called every x minites, or run on a loop.
	# Need to decide upon (and implement) how to encode time & duration with confession and adoration. Some sort of separating value? 
	global currentTime
	currentTime = datetime.datetime.now()
	hTime = 900
	if hTime != currentTime.strftime("%-H:%M"):
		print("Time Not Accurate - Testing Enabled")
	weekday = currentTime.strftime("%A")
	if weekday != currentTime.strftime("%A"):
		print("Day Not Accurate - Testing Enabled")
	print(weekday, hTime)

	#Defining Duration
	if weekday in WEEKDAYS:
		liturgyDuration = 30
	if weekday in WEEKEND:
		liturgyDuration = 60

	try:
		for parish in allocation.copy():
			print(parish)
			if hTime == masstime_database[parish[0]][weekday]:  #Check to see if they're having Mass
				display(parish[1], "mass", liturgyDuration)
			elif hTime == adoration_database[parish[0]][weekday]: #Check to see if Adoration is occuring
				display(parish[1], "adoration", "TBD")
			elif hTime == confession_database[parish[0]][weekday]: #Check to see if Confessions are being heard
				display(parish[1], "confession", "TBD")
			else:
				print("Nothing is happening right now at", parish[0])
	except KeyError as e:
		if str(e) == "0":
			print("Cycle Finished")
			pass
		else:
			raise
	#After everything, run the "update" command
	display("update", "update", "update")

def display(id, state, duration):
	#This will be called by chronos individually for each ID.
	#Must find LED assignment from key/id
	#Assign a LED its color, and store its duration & start time in variables.
	#When time is up, turn off the led.
	#Add logic to include some sort of a slow, randomized pulsing, so it's not just a static led display
	#Read the actual LED status, determine whether or not to clear it before assigning a new status.
	print(id, state, duration)
	if id == "update": #Runs only when all parishes have been cycled through.
		now = currentTime
		for value in ledStatus:
#			print(value, ledStatus[value][4])
			endtime = ledStatus[value][4]
			if now > endtime:
				ledStatus.pop(value)
				print("deleting ", value)
			#FILLER FOR TURNING OFF LED AT EXPIRATION
		#Future me, cycle through all of the timeStop values. (DONE) If expired, turn off light. (IN PROGRESS) remove id from ledStatus dictionary (DONE)
	else:	# Runs with the ifs and elifs in the try clause under chronos():
		timeStop = currentTime + timedelta(minutes=duration)
#		ledStatus[id] = [allocation[id - 1][2], state, currentTime.strftime("%-H%M"), duration, timeStop.strftime("%-H%M")]
		ledStatus[id] = [allocation[id - 1][2], state, currentTime, duration, timeStop]
		print(ledStatus)

setID()
ingest()
digest()
chronos()


'''
To do:

Vital
Import Mass Time Database
Parse Database - from JSON into local variables
assign ID to each LED / Parish
compare time to database entries
If time = database entry, light up LED
LED Driver:
	Different Colors
	Different Durations
	Different Animations (Pulsing, pusling on a offset, etc.)

Down the line:
SSH Callhome feature
Update times? Pull databse from self-hosted site?
LCD Character Display w/status

'''

