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
import logging
import mailer

# Easily accessible debug stuff
# Set debugSet to True to enable manual time/weekday. Set to false for realtime.
debugSet = False
DEBUG_TIME_SET = 2255
DEBUG_DAY = "Thursday"
logging.basicConfig(filename='info.log', format='%(levelname)s:%(message)s', level=logging.INFO)
if debugSet == True:
	logging.basicConfig(level=logging.DEBUG)

# Enable "Night Mode" - Map turns off during the time specified.
enableNightMode = True
nightModeStart = 2230
nightModeEnd = 700

#Variables we need to set go here:
stopLED = threading.Event()
JSON_LOCATION="./live.json"
LED_ALLOCATION="./leds.json"
DAYS=["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKDAYS=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKEND=["Saturday", "Sunday"]
ledStatus = {}
ledStatusStore = {}
pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness = 0.5)
quietLED = []
adorationLockout = []
threadIdentList = {}

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
			logging.info("Out of parishes, continuing...")
			pass
		else:
			raise
	finally:
		pass

#Combining Parish Name, ID, and LED Allocation into one dictionary
def setID():
	global allocation
	#creating a 2D array for the following data
	rows, cols = (190, 3)
	allocation = [[0 for i in range(cols)] for j in range(rows)]
	try:
		for key, id in iddict.items(): 		# key = parish name
			allocation[id["ID"] - 1][0] = key
			allocation[id["ID"] - 1][1] = id["ID"]
			allocation[id["ID"] - 1][2] = leddict.get(key) #LED Assignment
#			allocation[id["ID"] - 1][2] = id["ID"] # TEMPORARY! FOR TESTING
			if leddict.get(key)is None:
				print(key, leddict.get(key))
	except KeyError as e:
		if str(e) == 0:
			logging.warning("Key Error 0 on SetID, continuing")
			pass

def restart(parishID): 	# Restarting Adoration indicators (say if an event interrupts all day adoration, this is how it'll resume)
	global currentTime
	global adorationLockout
#	print("Attempting to restart", parishID)
	if debugSet == True:
		currentTime = DEBUG_TIME
		hTime = int(currentTime.strftime("%-H%M"))
		weekday = DEBUG_DAY
	else:
		currentTime = dt.datetime.now()
		hTime = int(currentTime.strftime("%-H%M"))
		weekday = currentTime.strftime("%A")

	try:
		for parish in allocation.copy():
			if parish[1] == parishID:
				parishData = parish

		if adoration_database[parishData[0]][weekday] is not None:
			var = adoration_database[parishData[0]][weekday].split(',')
			for _time in var[::2]:
				orig_length = int(var[var.index(_time) + 1])
				workingTime = datetime.strptime(str(int(_time)).zfill(3), "%H%M")
				workingEndTime = workingTime + timedelta(minutes=orig_length)
				workingTime_int = int(workingTime.strftime("%-H%M"))
				workingEndTime_int = int(workingEndTime.strftime("%-H%M"))
				if workingTime_int <= hTime <= workingEndTime_int:
					newDuration = workingEndTime - currentTime
					logging.debug('Restarting Adoration at %s for %s', parishData, newDuration)
					display(parish[1], "adoration", newDuration.total_seconds() / 60)
					length = int(var[var.index(_time) + 1])
					adorationLockout.append(parish[1])
					forceContinue = True
					continue
					if adoration_database[parishData[0]]["Is24hour"] is True and forceContinue == False and adorationLockout.count(parish[1]) == 0:
						display(parish[1], "adoration", "24h")
						adorationLockout.append(parish[1])
						continue
				else:
					pass
	except KeyError as e:		#Expected - reached the end of the list.
		if str(e) == "0":
			logging.info("Fyi - tried to reset 0 - caught")
			pass
		else:
			raise


def bootstrap(): 	#This will look very similar to chronos() below, though it serves a different purpose.
	global currentTime
	global adorationLockout
	logging.info("======== BOOTSTRAP START ========")
	if debugSet == True:
		currentTime = DEBUG_TIME
		hTime = int(currentTime.strftime("%-H%M"))
		weekday = DEBUG_DAY
		logging.debug("====== DEBUG MODE ON ======")
		logging.debug('Day: %s  weekday: %s', weekday, hTime)
	else:
		currentTime = dt.datetime.now()
		hTime = int(currentTime.strftime("%-H%M"))
		weekday = currentTime.strftime("%A")

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
					workingTime = datetime.strptime(str(int(_time)).zfill(3), "%H%M")
					workingEndTime = workingTime + timedelta(minutes=liturgyDuration)
					workingTime_int = int(workingTime.strftime("%-H%M"))
					workingEndTime_int = int(workingEndTime.strftime("%-H%M"))
					if workingTime_int <= hTime <= workingEndTime_int:
						newDuration = workingEndTime - currentTime
						logging.info('Mass at %s for %s', parish, newDuration)
						display(parish[1], "mass", newDuration.total_seconds() / 60)
						adorationLockout.append(parish[1])
						forceContinue = True
						continue
			if confession_database[parish[0]][weekday] is not None and forceContinue == False:
				var = confession_database[parish[0]][weekday].split(',')
				for _time in var[::2]:
					orig_length = int(var[var.index(_time) + 1])
					workingTime = datetime.strptime(str(int(_time)).zfill(3), "%H%M")
					workingEndTime = workingTime + timedelta(minutes=orig_length)
					workingTime_int = int(workingTime.strftime("%-H%M"))
					workingEndTime_int = int(workingEndTime.strftime("%-H%M"))
					if workingTime_int <= hTime <= workingEndTime_int:
						newDuration = workingEndTime - currentTime
						logging.info('Confession at %s for %s', parish, newDuration)
						display(parish[1], "confession", newDuration.total_seconds() / 60)
						adorationLockout.append(parish[1])
						forceContinue = True
						continue
			if adoration_database[parish[0]][weekday] is not None and forceContinue == False:
				var = adoration_database[parish[0]][weekday].split(',')
				for _time in var[::2]:
					orig_length = int(var[var.index(_time) + 1])
					workingTime = datetime.strptime(str(int(_time)).zfill(3), "%H%M")
					workingEndTime = workingTime + timedelta(minutes=orig_length)
					workingTime_int = int(workingTime.strftime("%-H%M"))
					workingEndTime_int = int(workingEndTime.strftime("%-H%M"))
					if workingTime_int <= hTime <= workingEndTime_int:
						newDuration = workingEndTime - currentTime
						logging.info('Adoration at %s for %s', parish, newDuration)
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
				logging.info("Cycled through all the parishes")
				pass
			else:
				raise
		except ValueError as e:		#Something is malformed in the JSON, and it can't be used
			logging.critical('%s %s - there is an issue here!!!', time, parish)
			raise

	display("update", "update", "update")
	logging.info("======== BOOTSTRAP END ========")

def chronos():
	global currentTime
	global adorationLockout
	if debugSet == True:
		currentTime = DEBUG_TIME
		hTime = int(currentTime.strftime("%-H%M"))
		weekday = DEBUG_DAY
		logging.debug("====== DEBUG MODE ON ======")
		logging.debug('Day: %s  Time: %s', weekday, hTime)
	else:
		currentTime = dt.datetime.now()
		hTime = int(currentTime.strftime("%-H%M"))
		weekday = currentTime.strftime("%A")
	logging.info('%s, %s', weekday, hTime)

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
						logging.debug('Calling for Mass at %s', parish[1])
						forceContinue = True
						continue
			if confession_database[parish[0]][weekday] is not None and forceContinue == False: #Confession times
				var = confession_database[parish[0]][weekday].split(',')
				for _time in var[::2]:
					if hTime == int(_time):
						length = int(var[var.index(_time) + 1])
						display(parish[1], "confession", length)
						logging.debug('Calling for Confession at %s', parish[1])
						adorationLockout.append(parish[1])
						forceContinue = True
						continue
			if adoration_database[parish[0]][weekday] is not None and forceContinue == False: #Adoration times
				var = adoration_database[parish[0]][weekday].split(',')
				for _time in var[::2]:
					if hTime == int(_time):
						length = int(var[var.index(_time) + 1])
						display(parish[1], "adoration", length)
						logging.debug('Calling for Adoration at %s', parish[1])
						forceContinue = True
						adorationLockout.append(parish[1])
						continue
			if adoration_database[parish[0]]["Is24hour"] is True and forceContinue == False and adorationLockout.count(parish[1]) == 0: #Perpetual Adoration
				display(parish[1], "adoration", "24h")
				adorationLockout.append(parish[1])
				continue
			else:
#				logging.debug("Nothing is happening right now at", parish[0])
				pass

		except AttributeError as e:	# Catches trying to read key that doesn't exist. Shouldn't need this anymore with valid JSON
			if str(e) == "'NoneType' object has no attribute 'keys'":
				raise
			else:
				raise

		except KeyError as e:		# Expected - At the end of the list.
			if str(e) == "0":
#				logging.info("Cycled through all the parishes")
				pass
			else:
				raise
		except ValueError as e:		# If data is malformed and unusable, this is raised.
			logging.critical('%s  %s  there is an issue here!!!', time, parish)
			break
	#After everything, run the "update" command. Signals that there are no more edits to the ledStore database in display().
	display("update", "update", "update")

def display(id, state, duration):
	global quietLED
	if id == "clean":	#Cleaning the board of outdated data.
		now = int(currentTime.strftime("%-H%M").zfill(3))
		for value in list(ledStatus):			#Value = ID!
			if ledStatus[value] is not None:
				endtime = ledStatus[value][4]
				if endtime != "24h":
					endtime = int(endtime.strftime("%-H%M"))	#Future me - this will probably break things, e.g. indicating Mass on top of adoration
#					if now > endtime:		#However, as of 5/18, it hasn't... ¯\_(ツ)_/¯
#						if state != "adoration":
#							print("Hey, something happened and value", value, "is past its endtime.")
					if now == endtime:
						ledStatus.pop(value)
						logging.info('deleting %s', value)
						for n in range(adorationLockout.count(value)):
							adorationLockout.remove(value)
		time.sleep(0.2)
	elif id != "update":	# Runs with the ifs and elifs in the try clause under chronos():
		if (duration == "24h"):
			timeStop = currentTime + timedelta(minutes=1339) #Soo... turn off the led in 1 day - 1 minute
			ledStatus[id] = [allocation[id - 1][2], state, currentTime, 0, timeStop]
		else:
			timeStop = currentTime + timedelta(minutes=duration)
			ledStatus[id] = [allocation[id - 1][2], state, currentTime, duration, timeStop]
#			print(ledStatus[id])
				#Check ledStatus and see what's new - In other words, look for a change and act accordingly.
	if id == "update":	#Runs only when all parishes have been cycled through
		if ledStatus != ledStatusStore:
			for key in list(ledStatus):				#Key = ID!
				try:				# \/ If an LED is already on, and something else is being commanded of it, first turn it off.
					if ledStatusStore.setdefault(key) is not None and ledStatus[key] != ledStatusStore[key]:
						logging.debug("LED off w/something new")
						ledStatusStore.pop(key)
						quietLED.append(key)
						time.sleep(0.01)
								# \/ If an LED is off and something wants it on, turn it on and log/store it
					if ledStatusStore.setdefault(key) is None and ledStatus[key] != ledStatusStore[key]:
						ledStatusStore[key] = ledStatus.get(key)
						if ledStatus[key] is not None: #Don't run a NoneType... That causes issues
							threading.Thread(target=driver, args=(ledStatus[key][0], ledStatus[key][1], key)).start()
				except KeyError:
					logging.error('There is a mismatch involving %s, might want to check it out.', key)
					raise
			for key in list(ledStatusStore):	# \/ If an LED is being set to off, turn it off.
				if ledStatus.setdefault(key) is None and ledStatusStore.setdefault(key) is not None:
					logging.info("Led off in update")
					counter = 0
					ledStatusStore.pop(key)
					quietLED.append(key)
					#Waiting for the led to be off / for it to no longer be in the list before continuing
					while quietLED.count(key) >= 1:
						time.sleep(0.01)
#						print("number of instances for", key, "in quietLED:", quietLED.count(key))
						counter = counter + 1
						if counter > 20:
							logging.error('Key %s has hung. Showing active threads...', key)
							logging.error('List of running threads: %s', threadIdentList)
							logging.error('Enumerated list of threads: %s', threading.enumerate())
#							print(threading.current_thread())
#							print(threading.get_ident())
							mailer.sendmail("MB Hung Thread", "A thread has hung.")
							break
					logging.info('set quietLED with ID: %s', key)
					restart(key)

def driver(led, state, id):
	#This is a Thread
#	print ("Starting", state, "indicator on LED", led, "with id", id)
	time.sleep(1) #To prevent a race condition, where a new thread follows commands (in quietLED) for an old thread
	updated = False
	threadIdentList.update({id: threading.get_ident()})
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
	if quietLED.count(id) >= 1:
		logging.debug('I can see a quietLED request for id: %s', id)
	while inhibit == False and stopLED.isSet() == False:
		try:
			if quietLED.count(id) >= 1:	# Turns off an LED
				pixels[led] = off
				quietLED.remove(id)
				logging.debug('off: %s  Updated Status: %s  ID: %s', led, updated, id)
#				time.sleep(0.1)
				threadIdentList.pop(id)
				break
			elif (updated == True):
				time.sleep(0.1)
				pass
			elif (style == "solid"):				# Sets an LED to a solid color
#				time.sleep(0.01)
				pixels[led] = color
				logging.debug('solid: %s', led)
				updated = True
			elif (style == "pulse"):				# Sets an LED to pulse
#				time.sleep(0.01)
				cos = breathingEffect(randomint)
				livecolor = (int(color[0] * cos), int(color[1] * cos), int(color[2] * cos))
				pixels[led] = livecolor
				pass
		except ValueError as e: #These are intermittent and random. I'd like to fix them, but they don't seem to cause much of an issue.
			logging.error('~~~~~ Value Error!: %s  %s  %s ~~~~~', led, state, id) #Only happens if it tries to turn off an LED, but it's already off.
			logging.error('Details: %s', e)
			#just in case...
			pixels[led] = off
			mailer.sendmail("MB Value Error", "There's been a value error. Check the logs for more info")
			raise
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
		inhibitLatch = False
		DEBUG_TIME = datetime.strptime(str(DEBUG_TIME_SET), "%H%M")
		bootstrap()
		logging.info("======== Letting Things Settle... ========")
		time.sleep(5)
		while debugSet == False:
			if storedTime != dt.datetime.now().strftime("%-H%M"):
				storedTime = dt.datetime.now().strftime("%-H%M")
				if enableNightMode == True:
					if int(storedTime) >= nightModeStart or int(storedTime) <= nightModeEnd:
						inhibit = True
						inhibitLatch = True
						time.sleep(0.1)
						pixels.fill(off)
					else:
						inhibit = False
						if inhibitLatch == True:
							inhibitLatch = False
							bootstrap()
				chronos()
				logging.info("Time Keeper Cycled")
			time.sleep(1)
			if stopLED.isSet() == True:
				logging.info("======== Powering Off LEDs ========")
				time.sleep(1)
				pixels.fill(off)
				break
		while debugSet == True:
			input("Press Enter to advance the time")
			chronos()
			time.sleep(0.1)
			DEBUG_TIME = DEBUG_TIME + timedelta(minutes=1)
			if stopLED.isSet() == True:
				logging.info("======== Powering Off LEDs ========")
				time.sleep(1)
				pixels.fill(off)
				break

	except:
		logging.critical("The map crashed with an error")
		pixels.fill(off)
		pixels[99] = (150, 0, 0)
		mailer.sendmail("Mapboard Error", "The mapboard is down due to an unspecified error.")
		raise

def startTimeKeeper():
	try:
		pleaseWork = threading.Thread(target=timeKeeper)
		pleaseWork.start()
		logging.info("Start the clock!")
		pleaseWork.join()
	except KeyboardInterrupt:
		print("\n\n\n======== Stopping the System ========")
		stopLED.set()
		logging.debug("======== Press Enter to Continue With the Shutdown ========")

try:
	ingest()
	setID()
	digest()
	startTimeKeeper()

except:
	logging.error("The map crashed with an error")
	pixels.fill(off)
	pixels[99] = (150, 0, 0)
	mailer.sendmail("Mapboard Error", "The mapboard is down due to an unspecified error.")
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
Add way to "restart" adoration after mass or confession, if not 24h
'''

