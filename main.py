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
BACKLIGHT_BRIGHTNESS = 0.3

# Easily accessible debug stuff
# Set debugSet to True to enable manual time/weekday. Set to false for realtime.
debugSet = True
DEBUG_TIME_SET = 1430
DEBUG_DAY = "Saturday"

# Configure logging - log to both stdout and file with timestamps and thread names
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(threadName)s: %(message)s'
LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'
LOG_FILE = 'mapboard.log'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if debugSet else logging.INFO)
logger.propagate = False  # Prevent duplicate logs to root logger

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG if debugSet else logging.INFO)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATEFMT))
logger.addHandler(console_handler)

# File handler (always logs everything)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATEFMT))
logger.addHandler(file_handler)

# Local development? Set to true if running on something other than the mapboard itself.
LOCAL_MODE = True

# Dry run mode - validates parish/LED mappings and exits without running
DRY_RUN = True

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
BACKLIGHT_BYPASS_NIGHT_MODE = False  # If True, backlight stays on during night mode

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
	logger.info("=== Starting data ingestion ===")
	parish_url = os.getenv("PARISH_DATA_URL")
	if parish_url:
		logger.info("Fetching parish data from URL: %s", parish_url)
		try:
			response = requests.get(parish_url, timeout=10)
			response.raise_for_status()
			rawjson = response.json()
			logger.info("Successfully fetched parish data from URL (%d parishes)", len(rawjson))
		except requests.exceptions.RequestException as e:
			logger.warning("Failed to fetch parish data from URL: %s. Falling back to local file.", e)
			with open(JSON_LOCATION, "r") as readfile:
				rawjson = json.load(readfile)
			logger.info("Loaded parish data from local file: %s (%d parishes)", JSON_LOCATION, len(rawjson))
	else:
		logger.info("No PARISH_DATA_URL set, loading from local file: %s", JSON_LOCATION)
		with open(JSON_LOCATION, "r") as readfile:
			rawjson = json.load(readfile)
		logger.info("Loaded parish data from local file (%d parishes)", len(rawjson))

	logger.info("Loading LED allocation from: %s", LED_ALLOCATION)
	leddict = json.loads(open(LED_ALLOCATION, "r").read())
	logger.info("Loaded LED mappings (%d entries)", len(leddict))
	iddict = rawjson
	logger.info("=== Data ingestion complete ===")

def getUnusedLEDs():
	"""Returns list of LED indices not used by parishes"""
	used_leds = set(leddict.values())
	all_leds = set(range(400))
	return list(all_leds - used_leds)

def turnOffParishLEDs():
	"""Turn off only parish LEDs, leaving backlight alone"""
	if LOCAL_MODE is False:
		for led in leddict.values():
			pixels[led] = (0, 0, 0)

def fetchLiturgicalColor():
	"""Fetches the current liturgical color from USCCB website"""
	url = os.getenv("LITURGICAL_COLOR_URL")
	if not url:
		logger.warning("LITURGICAL_COLOR_URL not set, skipping backlight")
		return None
	try:
		logger.info("Fetching liturgical color from: %s", url)
		response = requests.get(url, timeout=10)
		response.raise_for_status()
		logger.debug("Fetched %d bytes from USCCB", len(response.text))
		soup = BeautifulSoup(response.text, 'html.parser')

		# Method 1: Try data-colors attribute on first teaser link (today's reading)
		teaser_link = soup.select_one('li.teaser a[data-colors]')
		if teaser_link:
			color = teaser_link.get('data-colors')
			if color and color in LITURGICAL_COLORS:
				logger.info("Liturgical color (from data-colors): %s", color)
				return color
			logger.debug("data-colors found but value '%s' not recognized", color)

		# Method 2: Fall back to event-color span class
		color_span = soup.select_one('.four .event-color')
		if color_span:
			classes = color_span.get('class', [])
			logger.debug("event-color span classes: %s", classes)
			for cls in classes:
				if cls in LITURGICAL_COLORS:
					logger.info("Liturgical color (from event-color class): %s", cls)
					return cls

		# Debug: log what we did find
		teasers = soup.select('li.teaser')
		logger.warning("Could not find liturgical color. Found %d teaser elements", len(teasers))
		if teasers:
			logger.debug("First teaser HTML: %s", str(teasers[0])[:500])
		return None
	except Exception as e:
		logger.error("Error fetching liturgical color: %s", e, exc_info=True)
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

def dataRefreshWatcher():
	"""Thread that refreshes parish data daily at noon"""
	logger.info("dataRefreshWatcher thread starting")
	last_refresh_date = None
	while stopLED.is_set() == False and shutdown.is_set() == False:
		now = dt.datetime.now()
		today = now.date()
		current_hour = now.hour

		# Refresh at noon if we haven't already today
		if current_hour >= 12 and last_refresh_date != today:
			logger.info("dataRefreshWatcher: Refreshing parish data at noon")
			try:
				ingest()
				last_refresh_date = today
				logger.info("dataRefreshWatcher: Parish data refreshed successfully")
			except Exception as e:
				logger.error("dataRefreshWatcher: Failed to refresh data: %s", e)

		time.sleep(60)  # Check every minute
	logger.info("dataRefreshWatcher thread exiting")

def backlightWatcher():
	"""Thread that updates backlight color daily and handles night mode transitions"""
	logger.info("backlightWatcher thread starting")
	last_date = None
	was_in_night_mode = False
	current_color = None
	while stopLED.is_set() == False and shutdown.is_set() == False:
		today = dt.date.today()
		in_night_mode = nightLED.is_set()

		# Check if we need to refresh the backlight:
		# 1. New day
		# 2. Just exited night mode
		# 3. Bypass enabled and we're in night mode (re-apply after pixels.fill clears it)
		exited_night_mode = was_in_night_mode and not in_night_mode
		bypass_active = BACKLIGHT_BYPASS_NIGHT_MODE and in_night_mode

		if today != last_date:
			logger.info("backlightWatcher: Checking liturgical color for %s", today)
			color = fetchLiturgicalColor()
			if color:
				current_color = color
				if not in_night_mode or BACKLIGHT_BYPASS_NIGHT_MODE:
					setBacklight(color)
			else:
				logger.warning("backlightWatcher: No liturgical color fetched")
			last_date = today
		elif exited_night_mode and current_color:
			logger.info("backlightWatcher: Exited night mode, re-applying backlight")
			setBacklight(current_color)
		elif bypass_active and current_color:
			# Re-apply backlight during night mode when bypass is enabled
			setBacklight(current_color)

		was_in_night_mode = in_night_mode
		time.sleep(60)  # Check every minute to catch night mode transitions
	logger.info("backlightWatcher thread exiting")


#Combining Parish NotionID, ID, and LED Allocation into one dictionary
def setID():
	global allocation
	logger.info("=== Building parish-to-LED allocation map ===")
	#creating a 2D array for the following data
	rows, cols = (190, 3)
	allocation = [[0 for i in range(cols)] for j in range(rows)]
	missing_led = []  # Parishes without LED mapping (NotionID not in leds.json)
	orphan_led = set(leddict.keys())  # LEDs with no matching parish (will remove matches)
	parishes_processed = 0
	try:
		# JSON structure: key is NotionID, value has ID, Name, Mass Times, etc.
		for notionID in iddict:
			parishData = iddict[notionID]
			if parishData == {}:
				logger.warning("Empty record for NotionID: %s, skipping", notionID)
			else:
				parishID = parishData["ID"]
				parishName = parishData.get("Name", notionID)
				allocation[parishID - 1][0] = notionID  # Store NotionID for lookup
				allocation[parishID - 1][1] = parishID
				# Look up LED by NotionID
				led = leddict.get(notionID)
				allocation[parishID - 1][2] = led
				if led is None:
					missing_led.append((parishName, notionID))
				else:
					orphan_led.discard(notionID)
				parishes_processed += 1
		logger.info("Processed %d parishes", parishes_processed)
	except KeyError as e:
		logger.error("KeyError in setID while processing parish: %s", e, exc_info=True)
		if str(e) == 0:
			logger.warning("Key Error 0 on SetID, continuing")

	# Report mapping issues
	if missing_led:
		logging.warning("=== PARISHES MISSING LED MAPPINGS (%d) ===", len(missing_led))
		for name, notion_id in sorted(missing_led):
			logging.warning("  No LED mapping: %s (NotionID: %s)", name, notion_id)

	if orphan_led:
		logging.warning("=== ORPHAN LED ENTRIES (%d) - in leds.json but no matching NotionID ===", len(orphan_led))
		for notion_id in sorted(orphan_led):
			logging.warning("  Orphan LED %d: NotionID %s", leddict[notion_id], notion_id)

	if DRY_RUN:
		print("\n" + "="*60)
		print("DRY RUN SUMMARY")
		print("="*60)
		print(f"Total parishes in data: {len(iddict)}")
		print(f"Total LED mappings: {len(leddict)}")
		print(f"Parishes missing LED mappings: {len(missing_led)}")
		print(f"Orphan LED entries: {len(orphan_led)}")
		if missing_led:
			print("\n--- Parishes needing LED mapping ---")
			for name, notion_id in sorted(missing_led):
				print(f"  {name}")
				print(f"    NotionID: {notion_id}")
		if orphan_led:
			print("\n--- Orphan LED entries (NotionIDs in leds.json with no parish) ---")
			for notion_id in sorted(orphan_led):
				print(f"  NotionID: {notion_id} (LED {leddict[notion_id]})")
		print("="*60)
		sys.exit(0)

def liturgyLength(whatDayItIs):
	global liturgyDuration
	if whatDayItIs in WEEKDAYS:
		liturgyDuration = 30
	if whatDayItIs in WEEKEND:
		liturgyDuration = 60

def chronos2():
# All this is doing is advancing the time.
	logger.info("chronos2 clock thread starting")
	try:
		global currentTime, weekday, pocketWatchThread
		pocketWatchThread = threading.current_thread()
		aMinuteAgo = 0
		DEBUG_TIME = str(DEBUG_TIME_SET)
		logger.debug("chronos2: debugSet=%s, stopLED=%s, nightLED=%s", debugSet, stopLED.is_set(), nightLED.is_set())
		while debugSet == False and stopLED.is_set() == False and nightLED.is_set() == False:
			if aMinuteAgo != dt.datetime.now().strftime("%H%M"):
				aMinuteAgo = dt.datetime.now().strftime("%H%M")
				logger.info('Time tick: %s', aMinuteAgo)
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
			logger.info("Debug time advanced to: %s %s", DEBUG_TIME, weekday)
		logger.info('chronos2 exiting: weekday=%s, currentTime=%s', weekday, currentTime)
	except KeyboardInterrupt:
		logger.info("chronos2 received KeyboardInterrupt")
		raise
	except Exception as e:
		logger.error('Error in chronos2(): %s', e, exc_info=True)

def driver(led, state, EStop=""):
  if led is None:
    logger.debug("driver called with led=None, state=%s - skipping", state)
    return
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
        logger.debug('LED %s -> %s (color: %s)', led, state, color)
        updated = True
      elif (style == "pulse"):
      # Moved to thePastor for easier thread management Sets an LED to pulse
        pass
    except Exception as e:
      logger.error('Error in driver() for LED %s, state %s: %s', led, state, e, exc_info=True)
      raise

def fadingLED(led, color, stopEvent):
	if led is None:
		return
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
		logger.info("=== Starting clock thread (chronos2) ===")
		pocketWatch = threading.Thread(target=chronos2, name="Clock")
		pocketWatch.start()
		logger.info("Clock thread started successfully")
	except KeyboardInterrupt:
		logger.warning("KeyboardInterrupt in startTheClock")
		print("\n\n\n======== Stopping the System ========")
		stopLED.set()
		logger.debug("======== Press Enter to Continue With the Shutdown ========")

def watchTheClock():
	logger.debug("watchTheClock: Waiting for clock thread to finish")
	try:
		pocketWatchThread.join() #how do I join a thread that's already running? See .enumerate,.current_thread, etc. Can look through all threads, act on a certain one.
		logger.debug("watchTheClock: Clock thread joined")
		if nightLED.is_set():
			logger.info("watchTheClock: Entering night mode sleep loop")
			while checkNightMode() == True:
				if BACKLIGHT_BYPASS_NIGHT_MODE:
					turnOffParishLEDs()
				else:
					pixels.fill((0,0,0))
				time.sleep(60)
				logger.debug("watchTheClock: Still in night mode")
				continue
			if checkNightMode() == False:
				time.sleep(3) #Give the main thread a moment to notice that things switched back...
				logger.info("watchTheClock: Exiting night mode")
	except KeyboardInterrupt:
		print("\n\n\n======== Stopping the System ========")
		logger.warning('User initiated shutdown in watchTheClock')
		stopLED.set()
		logger.debug("======== Press Enter to Continue With the Shutdown ========")

def wakeUpParish():
	logger.info("=== Starting parish threads ===")
	thread_count = 0
	for parishID in allocation:
		# print(parishID)
		#if parishID[1] == 10: # For debugging individual parishes / only running one parish
		if parishID[0] != 0:
			thread_name = f"Parish-{parishID[1]}"
			t = threading.Thread(target=thePastor, args=([parishID[1], parishID[0], parishID[2]]), name=thread_name)
			t.start()
			thread_count += 1
	logger.info("Started %d parish threads", thread_count)

def clockmaker(strf):
	time = int(strf.strftime("%H%M"))
	return time

def checkNightMode():
	# If night mode is disabled, always return False
	if enableNightMode == False:
		return False
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
		return(False)

# This function runs for each parish. It's called and receives its assigned ID from wakeUpParish(),
# loads all of the applicable data (times, etc), watches the clock, and then as events come and go,
# commands leds to be powered on and off via driver()
def thePastor(id, notionID, led):
	global weekday, liturgyDuration
	logger.debug("thePastor starting: id=%s, notionID=%s, led=%s", id, notionID, led)
	try:
		parishCalendar = rawjson[notionID]
		name = parishCalendar.get("Name", f"Parish-{id}")
		logger.debug("Loaded calendar for %s (ID: %s)", name, id)
	except KeyError as e:
		logger.error("KeyError in thePastor - NotionID not found in rawjson: %s", notionID)
		return  # Exit gracefully instead of continuing with undefined parishCalendar
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
		logger.error("ID mismatch in thePastor! Expected %s but calendar has %s", id, parishCalendar["ID"])
		raise ValueError(f"ID mismatch: expected {id}, got {parishCalendar['ID']}")
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
			logger.info("KeyboardInterrupt in thePastor for parish %s", id)
			raise
		except Exception as e:
			logger.error('Exception in thePastor() for parish %s (notionID=%s, led=%s): %s',
						 id, notionID, led, e, exc_info=True)
			raise

def stopTheClock():
	signal.signal(signal.SIGINT, goToBed)
	signal.signal(signal.SIGTERM, goToBed)

def goToBed(*args):
	global stopLED
	logger.info("goToBed called with signal: %s", args[0] if args else "unknown")
	if args[0] == 2:
		print("\n\n\n======== Stopping the System - Ctrl C ========")
		if debugSet == True:
			print("======== (Press Enter...) ========")
		logger.warning('User initiated shutdown (SIGINT)')
		stopLED.set()
		shutdown.set()
	else:
		stopLED.set()
		shutdown.set()
		logger.warning('Shutting down due to signal: %s', args[0])

def parishUpdate(ID, action):
#	if action == "off":
#		print(ID, "off!!!")
#	return True
	global parishStatus
	if action == "verify":
		if ID in parishStatus:
			logger.debug("parishUpdate verify: parish %s already active (%s)", ID, parishStatus.get(ID))
			return False
		else:
			return True
	elif action == "reset":
		logger.info("parishUpdate: Resetting all parish statuses")
		parishStatus.clear()
	else:
		if action != "off":
			if ID in parishStatus:
				logger.error('parishUpdate: Conflict at parish %s - already has %s, tried to set %s',
							 ID, parishStatus[ID], action)
				raise AssertionError("Can't have two things going on at once")
			else:
				logger.info("parishUpdate: Parish %s -> %s", ID, action)
				parishStatus[ID] = action
		else:
			prev = parishStatus.get(ID, "unknown")
			logger.info("parishUpdate: Parish %s -> off (was: %s)", ID, prev)
			parishStatus.pop(ID, None)  # Use pop with default to avoid KeyError

try:
	logger.info("=" * 60)
	logger.info("=== MAPBOARD STARTING ===")
	logger.info("=" * 60)
	logger.info("Configuration: debugSet=%s, LOCAL_MODE=%s, DRY_RUN=%s", debugSet, LOCAL_MODE, DRY_RUN)
	logger.info("Night mode: enabled=%s, start=%s, end=%s, backlight_bypass=%s", enableNightMode, nightModeStart, nightModeEnd, BACKLIGHT_BYPASS_NIGHT_MODE)
	if debugSet:
		logger.info("Debug time: %s, Debug day: %s", DEBUG_TIME_SET, DEBUG_DAY)

	#Signal catching stuff
	parishClosing = stopTheClock()
	logger.info("Signal handlers registered")

	ingest()
	setID()

	# Start backlight with liturgical color
	logger.info("Starting backlight watcher thread")
	threading.Thread(target=backlightWatcher, daemon=True, name="Backlight").start()

	# Start data refresh watcher (refreshes parish data at noon)
	logger.info("Starting data refresh watcher thread")
	threading.Thread(target=dataRefreshWatcher, daemon=True, name="DataRefresh").start()

	global inhibit
	ticktock = 0
	logger.info("=== Entering main loop ===")
	while shutdown.is_set() == False:
		while checkNightMode() == False and stopLED.is_set() == False:
#		while checkNightMode() == False:
			logger.info("Main loop iteration starting (nightMode=False, stopLED=False)")
			nightLED.clear()
			startTheClock()
			time.sleep(1)
			wakeUpParish()
			watchTheClock()
			logger.debug("watchTheClock returned, sleeping 0.5s")
			time.sleep(0.5)
		if stopLED.is_set():
			logger.info("stopLED is set, turning off all LEDs")
			pixels.fill(off)
		while checkNightMode() == True and shutdown.is_set() == False:
			logger.debug("Night mode active, sleeping 5s")
			time.sleep(5)

	logger.info("=== Main loop exited (shutdown=%s) ===", shutdown.is_set())

except Exception as err:
	logger.exception("=" * 60)
	logger.exception("=== CRASH DETECTED ===")
	logger.exception("Exception type: %s", type(err).__name__)
	logger.exception("Exception message: %s", str(err))
	logger.exception("Active threads at crash: %d", threading.active_count())
	for t in threading.enumerate():
		logger.exception("  Thread: %s (alive=%s, daemon=%s)", t.name, t.is_alive(), t.daemon)
	logger.exception("=" * 60)
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
