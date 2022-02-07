#! /bin/python

#Things we need to import go here:
import json

#Variables we need to set go here:
JSON_LOCATION="./demo.json"
LED_ALLOCATION="./leds.txt"
PARISH_ID="./ids.txt"
WEEKDAYS=["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
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
			for day in WEEKDAYS: # Mass Times
				db1[day] = rawjson[parish[0]]['Mass Times'][day]
			masstime_database[parish[0]] = db1
			for day in WEEKDAYS: # Confession Times
				db2[day] = rawjson[parish[0]]['Confessions'][day]
			confession_database[parish[0]] = db2
			WEEKDAYS.append("is24hr")
			for day in WEEKDAYS: # Adoration Times
				db3[day] = rawjson[parish[0]]['Eucharistic Adoration'][day]
			adoration_database[parish[0]] = db3
			WEEKDAYS.remove("is24hr")
	except KeyError as e:
		if str(e) == "0":
			print("Out of parishes, continuing...")
			pass
		else:
			raise
	finally:
		print("Database entries:")
		print("\nMasses:", masstime_database)
		print("\nConfessions:", confession_database)
		print("\nAdoration:", adoration_database)
			#more to come later

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
		allocation[id - 1][2] = leddict.get(key)

setID()
ingest()
digest()


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

