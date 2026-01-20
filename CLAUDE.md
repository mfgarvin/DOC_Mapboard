# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mapboard is a real-time visualization system for the Catholic Diocese of Cleveland. It displays parish activities (Mass, Confession, Adoration) on a physical 30x40" map with ~400 individually addressable LEDs (APA106-F5) controlled by a Raspberry Pi 3B.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the main application
python main.py
```

## Environment Configuration

Copy `.env.example` to `.env` and configure:
- `PARISH_DATA_URL` - URL endpoint for parish schedule JSON (falls back to local `parish_data.json` if not set)
- `LITURGICAL_COLOR_URL` - URL to scrape liturgical color (e.g., `https://bible.usccb.org/`)

## Key Development Flags (in main.py)

- `debugSet = True` - Enables manual time control (press Enter to advance through time)
- `LOCAL_MODE = True` - Disables hardware access for development on non-Pi systems
- `enableNightMode = False` - Controls sleep behavior (normally 22:00-06:58)
- `DEBUG_TIME_SET = 1430` - Set manual test time (HHMM format)
- `DEBUG_DAY = "Saturday"` - Set manual test day

## Architecture

**Multi-threaded event-driven system:**
- One `thePastor()` thread per parish (~189 parishes)
- Central `chronos2()` clock thread for time advancement
- Night mode watchdog thread
- `backlightWatcher()` thread for liturgical color backlight on unused LEDs
- Shared state via thread Events and global dictionaries

**Key data structures:**
- `allocation` - 2D array mapping [parish_name, parish_id, led_address]
- `parishStatus` - dict tracking active activities per parish ID
- `rawjson` - parsed live.json with all parish schedules
- `leddict` - parsed leds.json LED address mapping

**LED color states (parish LEDs):**
- Blue (25, 125, 250) = Mass
- Purple (100, 10, 255) = Confession
- Gold (255, 255, 51) = Adoration (pulsing breathing effect)
- Off (0, 0, 0) = Idle

**Backlight (unused LEDs):**
- ~211 LEDs not assigned to parishes are used as ambient backlight
- Color is scraped daily from USCCB website (liturgical calendar color)
- Supported colors: green, white, red, purple/violet, rose, gold, black

## Key Files

- `main.py` - Core application with threading, LED control, and time tracking
- `converter.py` - Transforms raw parish data to internal JSON format
- `live.json` - Parish schedule data (mass times, confessions, adoration)
- `leds.json` - Maps parish names to LED addresses

## Utility Scripts (extras/)

- `calibrate.py` - LED hardware calibration (lights each LED sequentially)
- `off.py` - Turn off all LEDs
- `minigolf.py` - WebSocket-based LED demo/controller

## Dependencies

Hardware (Raspberry Pi only):
- `neopixel` - Adafruit LED control
- `board` - Adafruit GPIO abstraction

Data:
- `requests` - HTTP requests for remote data fetching
- `python-dotenv` - Environment variable loading from .env
- `beautifulsoup4` - HTML parsing for liturgical color scraping

## Important Implementation Notes

- Thread safety uses `parishUpdate()` for state verification to prevent race conditions
- Signal handlers (SIGINT/SIGTERM) provide graceful shutdown
- The `thePastor()` function is the core worker - understand it first when modifying behavior
- All configuration constants are at the top of main.py (no external config file)
