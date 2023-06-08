####
####            THIS IS A DEVELOPMENT FILE!
####
#! /bin/python
#Things we need to import go here:
import json
import datetime as dt
import time
from datetime import timedelta, datetime
import threading
from threading import Event
import logging
import board
import neopixel
import math
import random
import logging
import mailer
import sys

# Easily accessible debug stuff
# Set debugSet to True to enable manual time/weekday. Set to false for realtime.
debugSet = False
DEBUG_TIME_SET = 1459
DEBUG_DAY = "Saturday"
if debugSet == True:
  logging.basicConfig(level=logging.DEBUG)
else:
  logging.basicConfig(filename='infov3.log', format='%(levelname)s:%(message)s', level=logging.INFO)
#  logging.basicConfig(level=logging.INFO)
# Enable "Night Mode" - Map turns off during the time specified.
enableNightMode = True
nightModeStart = 2230
nightModeEnd = 658

#Variables we need to set go here:
stopLED = threading.Event()
JSON_LOCATION="./live.json"
LED_ALLOCATION="./leds.json"
DAYS=["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKDAYS=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKEND=["Saturday", "Sunday"]
weekday = ""
liturgyDuration = 0
ledStatus = {}
ledStatusStore = {}
pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness = 0.2)
#pixels = 0
quietLED = []
adorationLockout = []
threadIdentList = {}
#pocketWatchThread = 0

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
	readfile = open(JSON_LOCATION, "r")
	global rawjson, leddict, iddict
	rawjson = json.loads(readfile.read())
	leddict = json.loads(open(LED_ALLOCATION, "r").read())
	iddict = rawjson

#Combining Parish Name, ID, and LED Allocation into one dictionary
def setID():
	global allocation
	#creating a 2D array for the following data
	rows, cols = (189, 3)
	allocation = [[0 for i in range(cols)] for j in range(rows)]
	try:
		for key, id in iddict.items():          # key = parish name
			allocation[id["ID"] - 1][0] = key
			allocation[id["ID"] - 1][1] = id["ID"]
			allocation[id["ID"] - 1][2] = leddict.get(key) #LED Assignment
			if leddict.get(key)is None:
				logging.error('There is an issue with SetID')
	except KeyError as e:
		if str(e) == 0:
			logging.warning("Key Error 0 on SetID, continuing")
			raise

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
		while debugSet == False and stopLED.is_set() == False:
			if aMinuteAgo != dt.datetime.now().strftime("%H%M"):
				aMinuteAgo = dt.datetime.now().strftime("%H%M")
				print(aMinuteAgo)
				logging.info('The time is %s', aMinuteAgo)
				currentTime = dt.datetime.now()
				weekday = currentTime.strftime("%A")
				liturgyLength(weekday)
			else:
				time.sleep(1)
				if stopLED.is_set() == True:
					break
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
	while stopLED.is_set() == False and not stopEvent.is_set():
		cos = breathingEffect(randomint)
		livecolor = int(color[0] * cos), int(color[1] * cos), int(color[2] * cos)
		#logging.debug('fade: %s', led)
		pixels[led] = livecolor
		time.sleep(0.1)
	driver(led, 'off')

def breathingEffect(adjustment):        # Background code called by "pulse" above, supports the fading method.
	period = 20
	omega = 2 * math.pi / period
	phase = 0
	offset = 0.5
	amplitude = 0.5
	timer = time.time() + adjustment
	value = offset + amplitude * (math.cos((omega * timer) + phase))
	return(value)

def startTheClock():
	try:
		pocketWatch = threading.Thread(target=chronos2)
		pocketWatch.start()
		logging.info("Starting the pocketwatch")
		#pocketWatch.join()
	except KeyboardInterrupt:
		print("\n\n\n======== Stopping the System ========")
		stopLED.set()
		logging.debug("======== Press Enter to Continue With the Shutdown ========")

def watchTheClock():
	try:
		pocketWatchThread.join() #how do I join a thread that's already running? See .enumerate,.current_thread, etc. Can look through all threads, act on a certain one.
		if stopLED.is_set():
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
	#if parishID[1] == 4: # For debugging individual parishes / only running one parish
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
	parishCalendar = rawjson[name]
	notifyStart = False
	notifyProgress = False
	MresetEnable = False
	CresetEnable = False
	AresetEnable = False
	lockout1 = False
	lockout2 = False
	stopEvent = Event()
	HHActive = Event()
	flipflop = 0
	timeRemaining = 0
	if parishCalendar["ID"] != id:
		logging.error("There's an ID mismatch with thePastor!!!")
		raise
	while stopLED.is_set() == False:
		try:
			if checkNightMode() == True:
				stopLED.set()
				logging.info("Night Mode Enabled")
			localTime = clockmaker(currentTime)
			for activity in ("Mass", "Confession", "Adoration", "Adoration_24h"):
				if activity == "Mass" and lockout1 == False and lockout2 == False:
					massToday = parishCalendar["Mass Times"][weekday]
					if massToday is not None:
						for _time in massToday.split(','):
							if localTime != int(_time) and not liturgyDuration > localTime - int(_time) > 0:
								continue
							if localTime == int(_time) or liturgyDuration > localTime - int(_time) > 0:
								break
					else:
						_time = 9999
					if localTime == int(_time):
						if notifyStart == False:
							logging.info("Mass is starting")
							HHActive.clear()
							time.sleep(1)
							driver(led, 'mass')
							notifyStart = True
						MresetEnable = True
						break
					elif liturgyDuration > localTime - int(_time) > 0:
						timeRemaining = int(_time) + liturgyDuration - localTime
						if notifyProgress == False:
							logging.info("Mass is in progress")
							if notifyStart == False:
								HHActive.clear()
								time.sleep(1)
								driver(led, 'mass')
							notifyProgress = True
						MresetEnable = True
						break
					elif MresetEnable == True:
						print("Put some reset code here")
						MresetEnable = False
						notifyStart = False
						notifyProgress = False
						driver(led, 'off')
					else:
					# The end. This runs at idle.
						continue

				elif activity == "Confession" and lockout2 == False:
					if parishCalendar["Confessions"][weekday] is None:
						continue
					confessionsToday = []
					for value in parishCalendar["Confessions"][weekday].split(','):
						confessionsToday.append(value)
					times = confessionsToday[::2]
					durations = confessionsToday[1::2]
					for appointment in times:
						duration = int(confessionsToday[confessionsToday.index(appointment) + 1])
						appointment = int(appointment.strip())
						if localTime != appointment and not duration > localTime - appointment > 0:
							continue
						if localTime == appointment or duration > localTime - appointment > 0:
							break
					if localTime == appointment:
						if notifyStart == False:
							logging.debug("Confession is starting")
							HHActive.clear()
							time.sleep(1)
							driver(led, 'confession')
							notifyStart = True
							lockout1 = True
						CresetEnable = True
						break
					elif duration > localTime - appointment > 0:
						if notifyProgress == False:
							logging.debug("Confession is in progress")
							if notifyStart == False:
								HHActive.clear()
								time.sleep(1)
								driver(led, 'confession')
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
						driver(led, 'off')
					else:
					# Things are quiet. No confession is happening")
						continue

				elif activity == "Adoration":
					if parishCalendar["Adoration"]["Is24hour"] is None:
						if parishCalendar["Adoration"][weekday] is None:
							continue
						adorationToday = []
						for value in parishCalendar["Adoration"][weekday].split(','):
							adorationToday.append(value)
						times = adorationToday[::2]
						durations = adorationToday[1::2]
						for appointment in times:
							duration = int(adorationToday[adorationToday.index(appointment) + 1])
							appointment = int(appointment.strip())
							if localTime != appointment and not duration > localTime - appointment > 0:
								continue
							if localTime == appointment or duration > localTime - appointment > 0:
								break
						if localTime == appointment:
							if notifyStart == False:
								logging.debug("Adoration is starting")
								notifyStart = True
								lockout2 = True
								HHActive.clear()
								time.sleep(1)
								threading.Thread(target=fadingLED, args=(led, gold, stopEvent)).start()
							AresetEnable = True
							break
						elif duration > localTime - appointment > 0:
							if notifyProgress == False:
								logging.debug("Adoration is in progress")
								notifyProgress = True
								if notifyStart == False:
									HHActive.clear()
									time.sleep(1)
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
						else:
							# No hourly Adoration currently happening here.
							continue
					else:
						if flipflop == 0 and HHActive.is_set() == False:
							logging.debug('starting 24h for %s', led)
							HHActive.set()
							stopEvent.clear()
							threading.Thread(target=fadingLED, args=(led, gold, stopEvent)).start()
							flipflop = 1
							time.sleep(0.1)
						if HHActive.is_set() == False:
							logging.debug('stopping 24h for %s', led)
							stopEvent.set()
							flipflop = 0
							break
			time.sleep(1)
		except KeyboardInterrupt:
			raise
		except Exception as e:
			logging.error('Issue in thePastor(): %s', e)
			raise

try:
	ingest()
	setID()
	global inhibit
	while stopLED.is_set() == False:
		while checkNightMode() == False:
			print("looping at __main...")
			stopLED.clear()
			startTheClock()
			time.sleep(1)
			wakeUpParish()
			watchTheClock()
		if stopLED.is_set():
			pixels.fill(off)
		while checkNightMode() == True:
			print("Sleeping...")
			logging.debug("Sleeping... Currently in Night Mode")
			time.sleep(900)

except Exception as err:
#	err = sys.exc_info()[1]
	logging.critical("The map crashed with an error: %s", err)
	pixels.fill(off)
	pixels[99] = (150, 0, 0)
	mailer.sendmail("The Mapboard has Crashed", err)
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
