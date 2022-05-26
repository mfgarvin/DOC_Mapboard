#! /bin/python

#Things we need to import go here:
import json
import datetime as dt
import time
from datetime import timedelta, datetime
import threading
import logging
import board
import neopixel
import math
import random

# Easily accessible debug stuff
# Set debugSet to True to enable manual time/weekday. Set to false for realtime.
debugSet = False
DEBUG_TIME_SET = 2258
DEBUG_DAY = "Tuesday"

# Enable "Night Mode" - Map turns off during the time specified.
enableNightMode = False
nightModeStart = 2230
nightModeEnd = 700

#Variables we need to set go here:
stopLED = threading.Event()
JSON_LOCATION="./live.json"
LED_ALLOCATION="./leds.txt"
DAYS=["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKDAYS=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKEND=["Saturday", "Sunday"]
ledStatus = {}
ledStatusStore = {}
pixels = neopixel.NeoPixel(board.D21, 200, pixel_order=neopixel.RGB, brightness = 0.1)
quietLED = []
adorationLockout = []

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
	global allocation
	#creating a 2D array for the following data
	rows, cols = (191, 3)
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

def bootstrap(): 	#This will look very similar to chronos() below, though it serves a different purpose.
	print("======== BOOTSTRAP START ========")
	global currentTime
	global adorationLockout
	if debugSet == True:
		currentTime = DEBUG_TIME
		hTime = int(currentTime.strftime("%-H%M"))
		weekday = DEBUG_DAY
		print("====== DEBUG MODE ON ======")
		print("Day:", weekday, "Time:", hTime)
	else:
		currentTime = dt.datetime.now()
		hTime = int(currentTime.strftime("%-H%M"))
		weekday = currentTime.strftime("%A")

#	print(weekday, hTime)

	#Defining Duration
	if weekday in WEEKDAYS:
		liturgyDuration = 30
	if weekday in WEEKEND:
		liturgyDuration = 60

	for parish in allocation.copy():	#This checks to see if the present time is within the
		try:				#start/end time of an event, adjusts the duration accordingly,
			forceContinue = False	#and loads it.
			if masstime_database[parish[0]][weekday] is not None:
				for _time in masstime_database[parish[0]][weekday].split(','):
					workingTime = datetime.strptime(str(int(_time)), "%H%M")
					workingEndTime = workingTime + timedelta(minutes=liturgyDuration)
					workingTime_int = int(workingTime.strftime("%-H%M"))
					workingEndTime_int = int(workingEndTime.strftime("%-H%M"))
#					print(workingTime_int, workingEndTime_int)
					if workingTime_int <= hTime <= workingEndTime_int:
						newDuration = workingEndTime - workingTime
#						print("Running for:", newDuration, newDuration.total_seconds() / 60)
						display(parish[1], "mass", newDuration.total_seconds() / 60)
						adorationLockout.append(parish[1])
						forceContinue = True
						continue
			if confession_database[parish[0]][weekday] is not None and forceContinue == False:
				var = confession_database[parish[0]][weekday].split(',')
				for _time in var[::2]:
					orig_length = int(var[var.index(_time) + 1])
					workingTime = datetime.strptime(str(int(_time)), "%H%M")
					workingEndTime = workingTime + timedelta(minutes=orig_length)
					workingTime_int = int(workingTime.strftime("%-H%M"))
					workingEndTime_int = int(workingEndTime.strftime("%-H%M"))
#					print(workingTime_int, workingEndTime_int)
					if workingTime_int <= hTime <= workingEndTime_int:
						newDuration = workingEndTime - workingTime
#						print("Running for:", newDuration, newDuration.total_seconds() / 60)
						display(parish[1], "confession", newDuration.total_seconds() / 60)
						adorationLockout.append(parish[1])
						forceContinue = True
						continue
			if adoration_database[parish[0]][weekday] is not None and forceContinue == False:
				var = adoration_database[parish[0]][weekday].split(',')
				for _time in var[::2]:
					orig_length = int(var[var.index(_time) + 1])
					workingTime = datetime.strptime(str(int(_time)), "%H%M")
					workingEndTime = workingTime + timedelta(minutes=orig_length)
					workingTime_int = int(workingTime.strftime("%-H%M"))
					workingEndTime_int = int(workingEndTime.strftime("%-H%M"))
#					print(workingTime_int, workingEndTime_int)
					if workingTime_int <= hTime <= workingEndTime_int:
						newDuration = workingEndTime - workingTime
#						print("Running for:", newDuration, newDuration.total_seconds() / 60)
						display(parish[1], "adoration", newDuration.total_seconds() / 60)
						length = int(var[var.index(_time) + 1])
						adorationLockout.append(parish[1])
						forceContinue = True
						continue
			if adoration_database[parish[0]]["Is24hour"] is True and forceContinue == False and adorationLockout.count(parish[1]) == 0:
				display(parish[1], "adoration", "24h")
				adorationLockout.append(parish[1])
				continue
			else:
				pass
		except AttributeError as e:	#If there's something missing in the JSON
			if str(e) == "'NoneType' object has no attribute 'keys'":
				continue
			else:
				raise

		except KeyError as e:		#Expected - reached the end of the list.
			if str(e) == "0":
				print("Cycled through all the parishes")
				pass
			else:
				raise
		except ValueError as e:		#Something is malformed in the JSON, and it can't be used
			print(time, parish, "there's an issue here!!!")
			raise

	display("update", "update", "update")
	print("======== BOOTSTRAP END ========")

def chronos():
	global currentTime
	global adorationLockout
	if debugSet == True:
		currentTime = DEBUG_TIME
		hTime = int(currentTime.strftime("%-H%M"))
		weekday = DEBUG_DAY
		print("====== DEBUG MODE ON ======")
		print("Day:", weekday, "Time:", hTime)
	else:
		currentTime = dt.datetime.now()
		hTime = int(currentTime.strftime("%-H%M"))
		weekday = currentTime.strftime("%A")
	print(weekday, hTime)

	#Defining Duration
	if weekday in WEEKDAYS:
		liturgyDuration = 30
	if weekday in WEEKEND:
		liturgyDuration = 60

	#Clean the board of old data
	display("clean", "clean", "clean")

	for parish in allocation.copy():	# These check the current time against the start time of each
		try:				# event. If the time matches, set the duration and act accordingly.
			forceContinue = False
			if masstime_database[parish[0]][weekday] is not None:			#Mass times
				for _time in masstime_database[parish[0]][weekday].split(','):
					if hTime == int(_time):
						display(parish[1], "mass", liturgyDuration)
						adorationLockout.append(parish[1])
						forceContinue = True
						continue
			if confession_database[parish[0]][weekday] is not None and forceContinue == False: #Confession times
				var = confession_database[parish[0]][weekday].split(',')
				for _time in var[::2]:
					if hTime == int(_time):
						length = int(var[var.index(_time) + 1])
						display(parish[1], "confession", length)
						adorationLockout.append(parish[1])
						forceContinue = True
						continue
			if adoration_database[parish[0]][weekday] is not None and forceContinue == False: #Adoration times
				var = adoration_database[parish[0]][weekday].split(',')
				for _time in var[::2]:
					if hTime == int(_time):
						length = int(var[var.index(_time) + 1])
						display(parish[1], "adoration", length)
						forceContinue = True
						adorationLockout.append(parish[1])
						continue
			if adoration_database[parish[0]]["Is24hour"] is True and forceContinue == False and adorationLockout.count(parish[1]) == 0: #Perpetual Adoration
				display(parish[1], "adoration", "24h")
				adorationLockout.append(parish[1])
				continue
			else:
#				print("Nothing is happening right now at", parish[0])
				pass

		except AttributeError as e:	# Catches trying to read key that doesn't exist. Shouldn't need this anymore with valid JSON
			if str(e) == "'NoneType' object has no attribute 'keys'":
				raise
			else:
				raise

		except KeyError as e:		# Expected - At the end of the list.
			if str(e) == "0":
				print("Cycled through all the parishes")
				pass
			else:
				raise
		except ValueError as e:		# If data is malformed and unusable, this is raised.
			print(time, parish, "there's an issue here!!!")
			break
	#After everything, run the "update" command. Signals that there are no more edits to the ledStore database in display().
	display("update", "update", "update")

def display(id, state, duration):
	global quietLED
	if id == "clean":	#Cleaning the board of outdated data.
		now = currentTime
		for value in list(ledStatus):
			if ledStatus[value] is None:
				continue
			else:
				endtime = ledStatus[value][4]
				if endtime != "24h":			#Future me - this will probably break things, e.g. indicating Mass on top of adoration
					if now >= endtime:		#However, as of 5/18, it hasn't... ¯\_(ツ)_/¯
						ledStatus.pop(value)
#						print("deleting ", value)
						for n in range(adorationLockout.count(value)):
							adorationLockout.remove(value)
	elif id != "update":	# Runs with the ifs and elifs in the try clause under chronos():
		if (duration == "24h"):
			timeStop = currentTime + timedelta(weeks=52) #Soo... turn off the led in 1 year
			ledStatus[id] = [allocation[id - 1][2], state, currentTime, 0, timeStop]
		else:
			timeStop = currentTime + timedelta(minutes=duration)
			ledStatus[id] = [allocation[id - 1][2], state, currentTime, duration, timeStop]
				#Check ledStatus and see what's new - In other words, look for a change and act accordingly.
	if id == "update":	#Runs only when all parishes have been cycled through
		if ledStatus != ledStatusStore:
			for key in list(ledStatus):
				try:
					time.sleep(0.01)	# \/ If an LED is already on, and something else is being commanded of it, first turn it off.
					if ledStatusStore.setdefault(key) is not None and ledStatus[key] != ledStatusStore[key]:
						ledStatusStore.pop(key)
						quietLED.append(key)
								# \/ If an LED is off and something wants it on, turn it on and log/store it
					if ledStatusStore.setdefault(key) is None:
						ledStatusStore[key] = ledStatus.get(key)
						if ledStatus[key] is not None: #Don't run a NoneType... That causes issues
							threading.Thread(target=driver, args=(ledStatus[key][0], ledStatus[key][1], key)).start()
				except KeyError:
					print("There's some mismatch involving ", key,", might want to check it out.")
					raise
			for key in list(ledStatusStore):	# \/ If an LED is being set to off, turn it off.
				if ledStatus.setdefault(key) is None and ledStatusStore.setdefault(key) is not None:
					ledStatusStore.pop(key)
					quietLED.append(key)

def driver(led, state, id):
	#This is a Thread
#	print ("Starting", state, "indicator on LED", led)
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
	while inhibit == False and stopLED.isSet() == False:
		try:
			time.sleep(0.01)
			if (updated == True):
				time.sleep(0.1)
				pass
			elif (style == "solid"):				# Sets an LED to a solid color
				time.sleep(0.01)
				pixels[led] = color
				if debugSet == True:
					print("solid:", led)
				updated = True
			elif (style == "pulse"):				# Sets an LED to pulse
				time.sleep(0.01)
				cos = breathingEffect(randomint)
				livecolor = (int(color[0] * cos), int(color[1] * cos), int(color[2] * cos))
				pixels[led] = livecolor
				pass
			if quietLED.count(led) >= 1 or quietLED == "all":	# Turns off an LED
				pixels[led] = off
				quietLED.remove(led)
				if debugSet == True:
					print("off:", led)
				break
		except ValueError: #These are intermittent and random. I'd like to fix them, but they don't seem to cause much of an issue.
			print("######## Value Error!:", led, state, id, "########") #Only happens if it tries to turn off an LED, but it's already off.
			pass
	while inhibit == True:
		break

def breathingEffect(adjustment):	# Background code called by "pulse" above, supports the fading method.
	period = 20
	omega = 2 * math.pi / period
	phase = 0
	offset = 0.5
	amplitude = 0.5
	timer = time.time() + adjustment
	value = offset + amplitude * (math.cos((omega * timer) + phase))
	return(value)

def timeKeeper():		#This... keeps the time... Every minute, it calls chronos(), which updates
	#This is a thread	#the ledStore database and the board. If debugSet == True, then the time can
	try:			#be set and advanced manually.
		storedTime = 0
		global DEBUG_TIME
		global inhibit
		inhibit = False
		DEBUG_TIME = datetime.strptime(str(DEBUG_TIME_SET), "%H%M")
		bootstrap()
		print("======== Letting Things Settle... ========")
		time.sleep(5)
		while debugSet == False:
			if storedTime != dt.datetime.now().strftime("%-H%M"):
				storedTime = dt.datetime.now().strftime("%-H%M")
				if enableNightMode == True:
					if int(storedTime) >= nightModeStart or int(storedTime) <= nightModeEnd:
						inhibit = True
						time.sleep(0.1)
						pixels.fill(off)
					else:
						inhibit = False
				chronos()
				print("Time Keeper Cycled")
			time.sleep(1)
			if stopLED.isSet() == True:
				print("======== Powering Off LEDs ========")
				time.sleep(1)
				pixels.fill(off)
				break
		while debugSet == True:
			input("Press Enter to advance the time")
			chronos()
			time.sleep(0.1)
			DEBUG_TIME = DEBUG_TIME + timedelta(minutes=1)

	except:
		print ("The map crashed with an error")
		pixels.fill(off)
		pixels[0] = (150, 0, 0)
		raise

def startTimeKeeper():
	try:
		pleaseWork = threading.Thread(target=timeKeeper)
		pleaseWork.start()
		print("Start the clock!")
		pleaseWork.join()
	except KeyboardInterrupt:
		print("\n\n\n======== Stopping the System ========")
		stopLED.set()

try:
	ingest()
	setID()
	digest()
	startTimeKeeper()

except:
	print ("The map crashed with an error")
	pixels.fill(off)
	pixels[0] = (150, 0, 0)
	raise
'''
To do:

Down the line:
SSH Callhome feature - on the host os
Update times? Pull databse from self-hosted site?
LCD Character Display w/status
Different modes? Number of priests, parish size, etc.
Implement proper logging
Implement safe json verification
'''

