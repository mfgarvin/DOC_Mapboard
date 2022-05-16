import board
import neopixel

#How many LEDs are connected to the system?
#ledCount = 400
#ledCount = 30
ledCount = 100

pixels = neopixel.NeoPixel(board.D21, ledCount)

for n in range(ledCount):
	print("\n")
	print("LED Number:", n)
	pixels[n-1] = (0, 0, 0)
	pixels[n] = (255, 255, 255)
	input("Press Enter to advance")

print("Calibration Complete. Please populate leds.txt appropritely.")
pixels.fill((0, 0, 0))
