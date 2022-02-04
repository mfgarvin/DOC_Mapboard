#! /bin/python

#Things we need to import go here:
import json

#Variables we need to set go here:
JSON_LOCATION="./demo.json"
LED_ALLOCATION="./leds.txt"
PARISH_ID="./ids.txt"
#Functions? *Raises hand*
def ingest():
	readfile = open(JSON_LOCATION, "r")
	global rawjson
	rawjson = json.loads(readfile.read())

#def digest():
#This'll be breaking down the JSON into a giant dictionary

def setID():
	global allocation
	#creating a 2D array for the following data
	rows, cols = (200, 3)
	allocation = [[0 for i in range(cols)] for j in range(rows)]
	leddict = json.loads(open(LED_ALLOCATION, "r").read())
	iddict = json.loads(open(PARISH_ID, "r").read())
	print(leddict.items())
	print(iddict.items())
	for key, id in iddict.items(): 		# key = parish name
		allocation[id - 1][0] = key
		allocation[id - 1][1] = id
	for key, led in leddict.items():
		allocation[id - 1][2] = led
	allocation[0][2] = leddict.get("Our Lady of the Programmers") ### BUG - for key, led isn't placing LED value in the first array
	print(allocation)

# read both files (parish by LED and parish by ID), into two different vars
# sort both by name ("Stringd")
# append one to other, save as master dictionary


ingest()
#print(rawjson)
setID()



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

