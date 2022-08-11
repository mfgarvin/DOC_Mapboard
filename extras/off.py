import board
import neopixel

#How many LEDs are connected to the system?
#ledCount = 400
#ledCount = 30
ledCount = 200

pixels = neopixel.NeoPixel(board.D21, ledCount)

pixels.fill((0, 0, 0))
