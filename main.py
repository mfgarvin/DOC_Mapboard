#! /bin/python

#Things we need to import go here:
import json
import datetime
import time
from datetime import timedelta
import threading
import logging
import board
import neopixel
import math
import random

#Variables we need to set go here:
JSON_LOCATION="./live.json"
LED_ALLOCATION="./leds.txt"
DAYS=["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKDAYS=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKEND=["Saturday", "Sunday"]
ledStatus = {}
ledStatusStore = {}
pixels = neopixel.NeoPixel(board.D21, 200, pixel_order=neopixel.RGB, brightness=0.3)
quietLED = None
stopLED = False

#I'm gonna define LED colors here:
blue = (0, 0, 255)
purple = (100, 0, 255)
gold = (255, 255, 51)
off = (0, 0, 0)

#Functions? *Raises hand*
def ingest():
	readfile = open(JSON_LOCATION, "r")
	global rawjson, leddict, iddict
	rawjson = json.loads(readfile.read())
	leddict = json.loads(open(LED_ALLOCATION, "r").read())
	iddict = rawjson


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
			try:
				print(parish)
				for day in DAYS: # Mass Times
					db1[day] = rawjson[parish[0]]['Mass Times'][day]
				masstime_database[parish[0]] = db1
				db1 = {}
				for day in DAYS: # Confession Times
					db2[day] = rawjson[parish[0]]['Confessions'][day]
				confession_database[parish[0]] = db2
				db2 = {}
				DAYS.append("Is24hour")
				for day in DAYS: # Adoration Times
					db3[day] = rawjson[parish[0]]['Adoration'][day]
				adoration_database[parish[0]] = db3
				db3 = {}
				DAYS.remove("Is24hour")
			except:
				raise
#			except AttributeError:
#				pass
#			except TypeError:
#				pass
#			except KeyError:
#				pass
	except KeyError as e:
		if str(e) == "0":
			print("Out of parishes, continuing...")
			pass
		else:
			raise
	finally:
		pass
#		print(masstime_database)
#		print(confession_database)
#		print(adoration_database)

#Combining Parish Name, ID, and LED Allocation into one dictionary
def setID():
	global allocation
	#creating a 2D array for the following data
	rows, cols = (192, 3)
	allocation = [[0 for i in range(cols)] for j in range(rows)]
	try:
		for key, id in iddict.items(): 		# key = parish name
			allocation[id["ID"] - 1][0] = key
			allocation[id["ID"] - 1][1] = id["ID"]
#			allocation[id["ID"] - 1][2] = leddict.get(key) #LED Assignment
			allocation[id["ID"] - 1][2] = id["ID"] # TEMPORARY! FOR TESTING
	except KeyError as e:
		if str(e) == 0:
			print("Key Error 0 on SetID, continuing")
			pass

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
	hTime = currentTime.strftime("%-H%M")
	if hTime != currentTime.strftime("%-H%M"):
		print("Time Not Accurate - Testing Enabled")
	weekday = currentTime.strftime("%A")
#	weekday = "Saturday"
	if weekday != currentTime.strftime("%A"):
		print("Day Not Accurate - Testing Enabled")
	print(weekday, hTime)

	#Defining Duration
	if weekday in WEEKDAYS:
		liturgyDuration = 30
	if weekday in WEEKEND:
		liturgyDuration = 60

	for parish in allocation.copy(): #read each value check if time.
		try:
			if masstime_database[parish[0]][weekday] is not None:
				for time in masstime_database[parish[0]][weekday].split(','):
					if hTime == int(time):
						display(parish[1], "mass", liturgyDuration)
						continue
			if confession_database[parish[0]][weekday] is not None:
				var = confession_database[parish[0]][weekday].split(',')
				for time in var[::2]:
#					print (time)
#				for time, in confession_database[parish[0]][weekday].split(',')[::2]:
					if hTime == int(time):
						length = int(var[var.index(time) + 1])
						display(parish[1], "confession", length)
						continue
			if adoration_database[parish[0]]["Is24hour"] is True:
				display(parish[1], "adoration", "24h")
				continue
			if adoration_database[parish[0]][weekday] is not None:
				var = adoration_database[parish[0]][weekday].split(',')
				for time in var[::2]:
#				for time in adoration_database[parish[0]][weekday].split(',')[::2]:
					if hTime == int(time):
						length = int(var[var.index(time) + 1])
						display(parish[1], "adoration", length)
						continue
			else:
				print("Nothing is happening right now at", parish[0])
				pass
		except AttributeError as e: #This is raised if I try to get the value from something which has no value (e.g., getting the time when there is no time)
			if str(e) == "'NoneType' object has no attribute 'keys'":
#				continue
				raise
			else:
				raise

		except KeyError as e:
			if str(e) == "0":
				print("Cycled through all the parishes")
				pass
#			raise
			else:
				raise
		except ValueError as e:
			print(time, parish, "there's an issue here!!!")
			break 
	#After everything, run the "update" command. Signals that the database has been updated.
	display("update", "update", "update")

def display(id, state, duration):
	#This will be called by chronos individually for each ID. - DONE
	#Must find LED assignment from key/id - DONE
	#Assign a LED its color, and store its duration & start time in variables - DONE - Color assigned to driver().
	#When time is up, turn off the led.
	#Add logic to include some sort of a slow, randomized pulsing, so it's not just a static led display - Move to driver()!!!
	#Read the actual LED status, determine whether or not to clear it before assigning a new status. - Done in driver() via  ledstore comparison
	print("display() called:", id, state, duration)
	if id == "update": #Runs only when all parishes have been cycled through.
		now = currentTime
		for value in ledStatus:
#			print(value, ledStatus[value][4])
			endtime = ledStatus[value][4]
			if endtime != "24h":			#Future me - this will probably break things, e.g. indicating Mass on top of adoration
				if now > endtime:
					ledStatus.pop(value)
					print("deleting ", value)
		#Future me, cycle through all of the timeStop values. (DONE) If expired, turn off light. (DONE - In driver()) remove id from ledStatus dictionary (DONE)
	else:	# Runs with the ifs and elifs in the try clause under chronos():
		if (duration == "24h"):
			timeStop = currentTime + timedelta(weeks=52) #Soo... turn off the led in 1 year
			ledStatus[id] = [allocation[id - 1][2], state, currentTime, 0, timeStop]
		else:
			timeStop = currentTime + timedelta(minutes=duration)
#			ledStatus[id] = [allocation[id - 1][2], state, currentTime.strftime("%-H%M"), duration, timeStop.strftime("%-H%M")]
			ledStatus[id] = [allocation[id - 1][2], state, currentTime, duration, timeStop]
#		print("display() leddstatus:", ledStatus)
	#Check ledStatus and see what's new - In other words, look for a change and act accordingly.
	if ledStatus != ledStatusStore:
		for key in ledStatus:
			# If not in the Store but in the active dictionary, copy it over, then run it.
			if ledStatusStore.setdefault(key) is None:
				ledStatusStore[key] = ledStatus.get(key)
				threading.Thread(target=driver, args=(ledStatus[key][0], ledStatus[key][1], key)).start()
			#	driver(ledStatus[key][0], ledStatus[key][1], key)
				# Before I lose it, RIGHT HERE, run a command to start a thread with the set LED variables - DONE
				# (or refer to a different function to do it for you, to keep it clean) - DONE
				# Let this thread run, do the math, cycle the LED, etc. - DONE
				# Then, when the time runs out, kill the thread. - IN PROGRESS
		for key in ledStatusStore:
			# If in the store but not in the active directory (not M$), remove it
			if ledStatus.setdefault(key) is None:
				ledStatusStore.pop(key)
				quietLED = key

def driver(led, state, id):
	#This is a Thread
	print ("Starting", state, "indicator on LED", led)
	updated = False
	randomint = random.randint(-7, 7)
	if (state == "adoration"):
		style = "pulse"
		color = gold
		pass
	if (state == "mass"):
		style = "solid"
		color = blue
		pass
	if (state == "confession"):
		style = "solid"
		color = purple
		pass
	while True:
		time.sleep(0.01)
		if (updated == True):
			pass
		elif (style == "solid"):
			pixels[led] = color
			print("Color Set on", led, ":", color)
			updated = True
		elif (style == "pulse"):
			cos = int(breathingEffect(randomint))
			livecolor = (color[0] * cos, color[1] * cos, color[2] * cos)
#			print("Color Set on", led, ":", livecolor)
			pixels[led] = livecolor
			pass
		if quietLED == id or quietLED == "all":
			pixels[led] = off
#			quietLED = None
			break
			#turn off LED
		if stopLED == True: #Called at program quit
			pixels.fill(off)
			break

def breathingEffect(adjustment):
	period = 20
	omega = 2 * math.pi / period
	phase = 0
	offset = 0.5
	amplitude = 0.5
	timer = time.time() + adjustment
	value = offset + amplitude * (math.cos((omega * timer) + phase))
	return(value)

def timeKeeper():
	#This is a thread
	storedTime = 0
	while True:
		if storedTime != datetime.datetime.now().strftime("%-H%M"):
			storedTime = datetime.datetime.now().strftime("%-H%M")
			chronos()
			time.sleep(1)
			print("Time Keeper Cycled")

def startTimeKeeper():
	threading.Thread(target=timeKeeper).start()
	print("Start the clock!")

try:
	ingest()
	setID()
	digest()
	startTimeKeeper()
except KeyboardInterrupt:
	stopLED = True
	print("Stopping...")
	pixels.fill(off)
	time.sleep(2)
	sys.exit()
except:
	print ("The map crashed with an error")
	pixels.fill(off)
	pixels[0] = (150, 0, 0)
	raise
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
	Create a daemon function
	Use a sine function to create pulsing effect?

Down the line:
SSH Callhome feature
Update times? Pull databse from self-hosted site?
LCD Character Display w/status
Implement proper logging
Implement safe json verification
'''

