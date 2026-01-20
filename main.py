#! /bin/python
#Things we need to import go here:
import json
import datetime as dt
import time
from datetime import timedelta, datetime
import threading
from threading import Event
import logging
import math
import random
import logging
import sys
import signal
import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

# Liturgical color mappings (class name -> RGB)
LITURGICAL_COLORS = {
	"green": (0, 128, 0),
	"white": (255, 255, 255),
	"red": (255, 0, 0),
	"purple": (128, 0, 128),
	"violet": (128, 0, 128),
	"rose": (255, 105, 180),
	"gold": (255, 215, 0),
	"black": (25, 25, 25),
}
BACKLIGHT_BRIGHTNESS = 0.15

# Easily accessible debug stuff
# Set debugSet to True to enable manual time/weekday. Set to false for realtime.
debugSet = True
DEBUG_TIME_SET = 1430
DEBUG_DAY = "Saturday"
if debugSet == True:
  logging.basicConfig(level=logging.DEBUG)
else:
  logging.basicConfig(filename='info.log', format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)

# Local development? Set to true if running on something other than the mapboard itself.
LOCAL_MODE = True

if LOCAL_MODE is False:
	import board
	import neopixel

if LOCAL_MODE is True:
	class pixels:		#Creating a dummy pixels class
		def fill(x):
			pass

# Enable "Night Mode" - Map turns off during the time specified.
enableNightMode = False
nightModeStart = 2200
nightModeEnd = 658

#Variables we need to set go here:
stopLED = threading.Event()
nightLED = threading.Event()
shutdown = threading.Event()
JSON_LOCATION="./parish_data.json"
LED_ALLOCATION="./leds.json"
DAYS=["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKDAYS=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKEND=["Saturday", "Sunday"]
weekday = ""
liturgyDuration = 0
parishStatus = {}
if LOCAL_MODE is False:
	pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness = 0.2)
quietLED = []
adorationLockout = []
threadIdentList = {}

#I'm gonna define LED colors here:
blue = (25, 125, 250)
purple = (100, 10, 255)
gold = (255, 255, 51)
off = (0, 0, 0)

#I need to convert some integer time values to datetime values.
def convertToDT(value):
	#Converting to int and back to str for spacing issues.
	value = int(value)
	value = str(value)
	hour = int(time.strftime("%H", time.strptime(str(value).zfill(3), "%H%M")))
	minute = int(time.strftime("%M", time.strptime(str(value).zfill(3), "%H%M")))
	return dt.datetime.now().replace(hour=hour, minute=minute, second=0)

#Functions? *Raises hand*
def ingest():
	global rawjson, leddict, iddict
	parish_url = os.getenv("PARISH_DATA_URL")
	if parish_url:
		try:
			response = requests.get(parish_url, timeout=10)
			response.raise_for_status()
			rawjson = response.json()
		except requests.exceptions.RequestException as e:
			logging.warning("Failed to fetch parish data from URL: %s. Falling back to local file.", e)
			with open(JSON_LOCATION, "r") as readfile:
				rawjson = json.load(readfile)
	else:
		with open(JSON_LOCATION, "r") as readfile:
			rawjson = json.load(readfile)
	leddict = json.loads(open(LED_ALLOCATION, "r").read())
	iddict = rawjson

def getUnusedLEDs():
	"""Returns list of LED indices not used by parishes"""
	used_leds = set(leddict.values())
	all_leds = set(range(400))
	return list(all_leds - used_leds)

def fetchLiturgicalColor():
	"""Fetches the current liturgical color from USCCB website"""
	url = os.getenv("LITURGICAL_COLOR_URL")
	if not url:
		logging.warning("LITURGICAL_COLOR_URL not set, skipping backlight")
		return None
	try:
		response = requests.get(url, timeout=10)
		response.raise_for_status()
		soup = BeautifulSoup(response.text, 'html.parser')
		color_span = soup.select_one('.four .event-color')
		if color_span:
			classes = color_span.get('class', [])
			for cls in classes:
				if cls in LITURGICAL_COLORS:
					logging.info("Liturgical color: %s", cls)
					return cls
		logging.warning("Could not find liturgical color element")
		return None
	except Exception as e:
		logging.error("Error fetching liturgical color: %s", e)
		return None

def setBacklight(color_name):
	"""Sets all unused LEDs to the liturgical color"""
	if color_name not in LITURGICAL_COLORS:
		logging.warning("Unknown liturgical color: %s", color_name)
		return
	rgb = LITURGICAL_COLORS[color_name]
	dimmed = tuple(int(c * BACKLIGHT_BRIGHTNESS) for c in rgb)
	unused_leds = getUnusedLEDs()
	logging.info("Setting %d backlight LEDs to %s", len(unused_leds), color_name)
	if LOCAL_MODE is False:
		for led in unused_leds:
			pixels[led] = dimmed

def backlightWatcher():
	"""Thread that updates backlight color daily"""
	last_date = None
	while stopLED.is_set() == False and shutdown.is_set() == False:
		today = dt.date.today()
		if today != last_date:
			color = fetchLiturgicalColor()
			if color:
				setBacklight(color)
			last_date = today
		time.sleep(3600)  # Check every hour


#Combining Parish Name, ID, and LED Allocation into one dictionary
def setID():
	global allocation
	#creating a 2D array for the following data
	rows, cols = (189, 3)
	allocation = [[0 for i in range(cols)] for j in range(rows)]
	try:
		for parishName in iddict:
			if iddict[parishName] == {}:
				print("The record seems to be empty for " + parishName +", continuing...")
			else:
				parishID = iddict[parishName]["ID"]
				allocation[parishID - 1][0] = parishName
				allocation[parishID - 1][1] = parishID
				allocation[parishID - 1][2] = leddict.get(parishName)
	except KeyError as e:
		if str(e) == 0:
			logging.warning("Key Error 0 on SetID, continuing")

def liturgyLength(whatDayItIs):
	global liturgyDuration
	if whatDayItIs in WEEKDAYS:
		liturgyDuration = 30
	if whatDayItIs in WEEKEND:
		liturgyDuration = 60

def chronos2():
# All this is doing is advancing the time.
	try:
		global currentTime, weekday, pocketWatchThread
		pocketWatchThread = threading.current_thread()
		aMinuteAgo = 0
		DEBUG_TIME = str(DEBUG_TIME_SET)
		while debugSet == False and stopLED.is_set() == False and nightLED.is_set() == False:
			if aMinuteAgo != dt.datetime.now().strftime("%H%M"):
				aMinuteAgo = dt.datetime.now().strftime("%H%M")
				print(aMinuteAgo)
#				logging.info('%s %s %s', stopLED.is_set(), nightLED.is_set(), shutdown.is_set())
				logging.debug('The time is %s', aMinuteAgo)
				currentTime = dt.datetime.now()
				weekday = currentTime.strftime("%A")
				liturgyLength(weekday)
			else:
				time.sleep(1)
#				if stopLED.is_set() == True or nightLED.is_set() == True:
#					break
		while debugSet == True and stopLED.is_set() == False:
			currentTime = convertToDT(DEBUG_TIME)   #Note - something here breaks at midnight?
			weekday = DEBUG_DAY
			liturgyLength(weekday)
			input("Press Enter to advance the time")
			time.sleep(0.1)
			DEBUG_TIME = convertToDT(DEBUG_TIME) + timedelta(minutes=1)
			DEBUG_TIME = DEBUG_TIME.strftime("%H%M")
			print(DEBUG_TIME, weekday)
		logging.debug('%s, %s', weekday, currentTime)
	except KeyboardInterrupt:
		raise
	except Exception as e:
		logging.error('Error in chronos2(): %s', e)

def driver(led, state, EStop=""):
  updated = False
  stopEvent = Event()
  if (state == "adoration"):
  # style = "pulse"
  # color = gold
  # Moved to thePastor for the sake of easier thread control
    pass
  if (state == "mass"):
    style = "solid"
    color = blue
    pass
  if (state == "confession"):
    style = "solid"
    color = purple
    pass
  if (state == "off"):
    style = "solid"
    color = off
    pass
  if stopLED.is_set() == False:
    try:
      if (style == "solid"):                                # Sets an LED to a solid color
        if LOCAL_MODE is False:
          pixels[led] = color
        logging.debug('solid: %s, color: %s', led, color)
        updated = True
      elif (style == "pulse"):
      # Moved to thePastor for easier thread management Sets an LED to pulse
        pass
    except Exception as e:
      logging.error('Error in driver(): %s', e)
      raise

def fadingLED(led, color, stopEvent):
	randomint = random.randint(-7, 7)
	while stopLED.is_set() == False and not stopEvent.is_set() and nightLED.is_set() == False:
#		if int(round(time.time(), 2) * 100) % 10== led % 10:
		cos = breathingEffect(randomint)
		livecolor = int(color[0] * cos), int(color[1] * cos), int(color[2] * cos)
		#logging.debug('fade: %s', led)
		if LOCAL_MODE is False:
			pixels[led] = livecolor
		#time.sleep(0.1)
#		if led == 160:
#			print(livecolor)
#		else:
#			pass
#			time.sleep(0.05)
	driver(led, 'off')

def breathingEffect(adjustment):        # Background code called by "pulse" above, supports the fading method.
	period = 20
	omega = 2 * math.pi / period
	phase = 0
	offset = 0.5
	amplitude = 0.5
	timer = time.time() + adjustment
	value = offset + amplitude * (math.cos((omega * timer) + phase))
#	time.sleep(0.1)
	return(value)

def startTheClock():
	try:
		pocketWatch = threading.Thread(target=chronos2)
		pocketWatch.start()
		logging.info("Starting the Display")
		#pocketWatch.join()
	except KeyboardInterrupt:
		print("\n\n\n======== Stopping the System ========")
		stopLED.set()
		logging.debug("======== Press Enter to Continue With the Shutdown ========")

def watchTheClock():
	try:
		pocketWatchThread.join() #how do I join a thread that's already running? See .enumerate,.current_thread, etc. Can look through all threads, act on a certain one.
		if nightLED.is_set():
			while checkNightMode() == True:
				pixels.fill((0,0,0))
				time.sleep(60)
				logging.debug("watch the clock has gone into sleep mode")
				continue
			if checkNightMode() == False:
				time.sleep(3) #Give the main thread a moment to notice that things switched back...
				logging.debug("Watch The clock has gone out of sleep mode.")
	except KeyboardInterrupt:
		print("\n\n\n======== Stopping the System ========")
		logging.info('User initiated shutdown')
		stopLED.set()
		logging.debug("======== Press Enter to Continue With the Shutdown ========")

def wakeUpParish():
	for parishID in allocation:
		# print(parishID)
		#if parishID[1] == 10: # For debugging individual parishes / only running one parish
		if parishID[0] != 0:
			threading.Thread(target=thePastor, args=([parishID[1], parishID[0], parishID[2]])).start()

def clockmaker(strf):
	time = int(strf.strftime("%H%M"))
	return time

def checkNightMode():
	if debugSet == False:
		time = clockmaker(dt.datetime.now())
		if time > nightModeStart:
			return(True)
		if nightModeEnd > time:
			parishUpdate(1000, "reset")
			return(True)
		else:
			return(False)
	else:
#		time = clockmaker(dt.datetime.now())
#		if nightModeStart > time > nightModeEnd:
#			return(True)
#		else:
#			return(False)
		return(False)

# This function runs for each parish. It's called and receives its assigned ID from wakeUpParish(), 
# loads all of the applicable data (times, etc), watches the clock, and then as events come and go,
# commands leds to be powered on and off via driver()
def thePastor(id, name, led):
	global weekday, liturgyDuration
	try:
		parishCalendar = rawjson[name]
	except KeyError as e:
		print("Key Error for" + str(name))
	notifyStart = False
	notifyProgress = False
	MresetEnable = False
	CresetEnable = False
	AresetEnable = False
	lockout1 = False
	lockout2 = False
	stopEvent = Event()
#	stopEvent.set()
	HHActive = Event()
	flipflop = 0
	timeRemaining = 0
	if parishCalendar["ID"] != id:
		logging.error("There's an ID mismatch with thePastor!!!")
		raise
	while stopLED.is_set() == False and nightLED.is_set() == False:
		try:
			if checkNightMode() == True:
				nightLED.set()
				logging.info("Night Mode Enabled")
			localTime = clockmaker(currentTime)
			for activity in ("Mass", "Confession", "Adoration", "Adoration_24h"):
				time.sleep(0.25)
				if activity == "Mass" and lockout1 == False and lockout2 == False:
					if parishCalendar["Mass Times"] == {}:
						continue
					if parishCalendar["Mass Times"].get(weekday) is None:
						continue
					massToday = parishCalendar["Mass Times"][weekday]
					if massToday is not None:
						# for _time in massToday.split(','):
						for _time in massToday:
							if localTime != int(_time) and not liturgyDuration > localTime - int(_time) > 0:
								continue
							if localTime == int(_time) or liturgyDuration > localTime - int(_time) > 0:
								break
					else:
						_time = 9999
					if localTime == int(_time):
						if notifyStart == False:
							logging.debug("Mass is starting - %s - %s", name, id)
							if not stopEvent.is_set() and HHActive.is_set(): #AKA only if 24h adoration is happening and needs to be interrupted...
								HHActive.clear()
								stopEvent.set()
								parishUpdate(id, "off")
							time.sleep(1)
							if parishUpdate(id, "verify") is True:
								driver(led, 'mass')
								notifyStart = True
								parishUpdate(id, "mass")
						MresetEnable = True
						break
					elif liturgyDuration > localTime - int(_time) > 0:
						timeRemaining = int(_time) + liturgyDuration - localTime
						if notifyProgress == False:
							logging.debug("Mass is in progress - %s - %s", name, id)
							if notifyStart == False:
								if not stopEvent.is_set() and HHActive.is_set(): #AKA only if 24h adoration is happening and needs to be interrupted...
									HHActive.clear()
									stopEvent.set()
									parishUpdate(id, "off")
								time.sleep(1)
								if parishUpdate(id, "verify") is True:
									driver(led, 'mass')
									parishUpdate(id, "mass")
							notifyProgress = True
						MresetEnable = True
						break
					elif MresetEnable == True:
						MresetEnable = False
						notifyStart = False
						notifyProgress = False
						driver(led, 'off')
						parishUpdate(id, "off")
#						stopEvent.clear()
					else:
					# The end. This runs at idle.
						continue

				elif activity == "Confession" and lockout2 == False:
					if parishCalendar["Confessions"] == {}:
						continue
					if parishCalendar["Confessions"].get(weekday) is None:
						continue
					confessionsToday = []
					for value in parishCalendar["Confessions"][weekday]:
						timeOfDay = list(value.keys())
						confDuration = list(value.values())
						confessionsToday.append(int(timeOfDay[0]))
						confessionsToday.append(confDuration[0])
					times = confessionsToday[::2]
					durations = confessionsToday[1::2]
					for appointment in times:
						duration = int(confessionsToday[confessionsToday.index(appointment) + 1])
						# appointment = int(appointment.strip())
						if localTime != appointment and not duration > localTime - appointment > 0:
							continue
						if localTime == appointment or duration > localTime - appointment > 0:
							break
					if localTime == appointment:
						if notifyStart == False:
							if not stopEvent.is_set() and HHActive.is_set(): #AKA only if 24h adoration is happening and needs to be interrupted...
								HHActive.clear()
								stopEvent.set()
								parishUpdate(id, "off")
							time.sleep(1)
							if parishUpdate(id, "verify") is True:
								logging.debug("Confession is starting - %s - %s", name, id)
								driver(led, 'confession')
								parishUpdate(id, "conf")
								notifyStart = True
								lockout1 = True
						CresetEnable = True
						break
					elif duration > localTime - appointment > 0:
						if notifyProgress == False:
							logging.debug("Confession is in progress - %s - %s", name, id)
							if notifyStart == False:
								if not stopEvent.is_set() and HHActive.is_set(): #AKA only if 24h adoration is happening and needs to be interrupted...
									HHActive.clear()
									stopEvent.set()
									parishUpdate(id, "off")
								time.sleep(1)
								if parishUpdate(id, "verify") is True:
									HHActive.clear()
									time.sleep(1)
									driver(led, 'confession')
									parishUpdate(id, "conf")
							notifyProgress = True
							lockout1 = True
						CresetEnable = True
						break
					elif CresetEnable == True:
						# Reset code goes here.
						notifyStart = False
						notifyProgress = False
						CresetEnable = False
						lockout1 = False
						duration = 0
						appointment = 0
#						stopEvent.clear()
						driver(led, 'off')
						parishUpdate(id, "off")
					else:
					# Things are quiet. No confession is happening")
						continue
				
				elif activity == "Adoration":
					if parishCalendar["Adoration"] == {}:
						continue
					if parishCalendar["Adoration"].get("Is24Hour") is None:
						if parishCalendar["Adoration"].get(weekday) is None:
							continue
						adorationToday = []
						for value in parishCalendar["Adoration"][weekday]:
							timeOfDay2 = list(value.keys())
							adoreDuration = list(value.values())
							adorationToday.append(int(timeOfDay2[0]))
							adorationToday.append(adoreDuration[0])
						times = adorationToday[::2]
						durations = adorationToday[1::2]
						for appointment in times:
							duration = int(adorationToday[adorationToday.index(appointment) + 1])
							if localTime != appointment and not duration > localTime - appointment > 0:
								continue
							if localTime == appointment or duration > localTime - appointment > 0:
								break
						if localTime == appointment:
							if notifyStart == False and parishUpdate(id, "verify") is True:
								logging.debug("Adoration is starting")
								notifyStart = True
								lockout2 = True
								HHActive.clear()
								time.sleep(1)
								parishUpdate(id, "adore")
								threading.Thread(target=fadingLED, args=(led, gold, stopEvent)).start()
							AresetEnable = True
							break
						elif duration > localTime - appointment > 0:
							if notifyProgress == False:
								logging.debug("Adoration is in progress")
								notifyProgress = True
								if notifyStart == False and parishUpdate(id, "verify") is True:
									HHActive.clear()
									time.sleep(1)
									parishUpdate(id, "adore")
									threading.Thread(target=fadingLED, args=(led, gold, stopEvent)).start()
								lockout2 = True
							AresetEnable = True
							break
						elif AresetEnable == True:
							# Reset code goes here.
							notifyStart = False
							notifyProgress = False
							AresetEnable = False
							lockout2 = False
							duration = 0
							appointment = 0
							stopEvent.set()
							parishUpdate(id, "off")
						else:
							# No hourly Adoration currently happening here.
							continue
					elif parishCalendar["Adoration"]["Is24Hour"] == True:
						if flipflop == 0 and HHActive.is_set() == False and parishUpdate(id, "verify") is True:
							logging.debug('starting 24h for %s', led)
							HHActive.set()
							stopEvent.clear()
							threading.Thread(target=fadingLED, args=(led, gold, stopEvent)).start()
							parishUpdate(id, "adore24")
							flipflop = 1
							time.sleep(0.1)
						if HHActive.is_set() == False:
							logging.debug('stopping 24h for %s', led)
							stopEvent.set()
#							parishUpdate(id, "off")
							flipflop = 0
							break
			time.sleep(15)
		except KeyboardInterrupt:
			raise
		except Exception as e:
			logging.error('Issue in thePastor(): %s', e)
			raise

def stopTheClock():
	signal.signal(signal.SIGINT, goToBed)
	signal.signal(signal.SIGTERM, goToBed)

def goToBed(*args):
	global stopLED
	if args[0] == 2:
		print("\n\n\n======== Stopping the System - Ctrl C ========")
		if debugSet == True:
			print("======== (Press Enter...) ========")
		logging.warning('User initiated shutdown\n')
		stopLED.set()
		shutdown.set()
	else:
		stopLED.set()
		shutdown.set()
		logging.warning('Shutting Down - %s\n', args[0])

def parishUpdate(ID, action):
#	if action == "off":
#		print(ID, "off!!!")
#	return True
	global parishStatus
	if action == "verify":
		if ID in parishStatus:
			return False
		else:
			return True
	elif action == "reset":
		parishStatus.clear()
	else:
		if action != "off":
			if ID in parishStatus:
				logging.error('Tried to do too much at %s', ID)
				raise AssertionError("Can't have two things going on at once")
			else:
				parishStatus[ID] = action
		else:
			parishStatus.pop(ID)

try:
	#Signal catching stuff
	parishClosing = stopTheClock()

	ingest()
	setID()

	# Start backlight with liturgical color
	threading.Thread(target=backlightWatcher, daemon=True).start()

	global inhibit
	ticktock = 0
	while shutdown.is_set() == False:
		while checkNightMode() == False and stopLED.is_set() == False:
#		while checkNightMode() == False:
			print("looping at __main...")
			nightLED.clear()
			startTheClock()
			time.sleep(1)
			wakeUpParish()
			watchTheClock()
			time.sleep(0.5)
		if stopLED.is_set():
			pixels.fill(off)
		while checkNightMode() == True and shutdown.is_set() == False:
			logging.debug("Sleeping... Currently in Night Mode")
			time.sleep(5)

except Exception as err:
#	err = sys.exc_info()[1]
	logging.exception("############ Crash! :/ ############")
	pixels.fill(off)
	if LOCAL_MODE is False:
		pixels[99] = (150, 0, 0)
	raise
'''
To do:

Down the line:
SSH Callhome feature - on the host os
Update times? Pull databse from self-hosted site?
LCD Character Display w/status
Different modes? Number of priests, parish size, etc.
Implement safe json verification

As of 5/18/23
Reconfigure error handling
fix hang on keyboard interrupt
fix indents: Inconsistency and revise to tabs
Night Mode - Doesn't work yet?
Improve logging
Add verification that all parish threads are running?

'''
