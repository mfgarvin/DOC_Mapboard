# Mapboard
## A Digital Statusboard / Map of the Catholic Diocese of Cleveland

Hello!
Welcome to Mapboard, a statusboard / map of sorts for visualizing the goings on of the Catholic Diocese of Cleveland at any given moment.

### What is it?
This is the software side, written entirely in Python, of a hybrid analog/digital map of the diocese. I collected data for all ~180 parishes in the diocese, complied it, and push it out to a hardware interface for visualization (See below for a photo).

### How does it work?
Over the course of a couple months, I gathered the mass times, confession times, and adoration times for each parish in the diocese. This code polls that data, and indicates what's going on at a particular parish at a particular time. In doing so for each parish, I'm able to visualize what's going on throughout the diocese at any particular point in time.

### What does the physical interface look like?
There's not much of an interface to speak of, in that there's nothing to physically adjust and "interface" with. 

### Fine then. What does it look like?
Here's a photo! The map itself is about 30" by 40", with an individually addressable LED at the location of each Catholic Church in the area. As something occurs at that parish (Mass, Confession, and Adoration for now), that particular LED turns a certain color, so you can see what's going on.
![Image of the map](https://storage.googleapis.com/copper_public_archive/github/mapboard.jpg)

### Hardware Components
- Raspberry Pi 3B
- Custom Wooden Frmae
- Custom Map
- 500 APA106-F5 Addressable LEDs (As these came prewired in strands, most are hanging out behind the map.
- Some Hot Glue
- 5V, 20A Power Supply
- Misc Wiring, Bus Bars
- An Adafruit Quad Level-Shifter, to shift the Pi's GPIO 3v signal to 5v

### What else can it do?
Not much else for now... Theoretically, with the framework placed, I could feed it any dataset and have it display it by parish (number of families, number of priests, etc.), however for now it just displays parish activities in real-time.
