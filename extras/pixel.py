import board
import neopixel
pixels = neopixel.NeoPixel(board.D21, 400, brightness=1)
#T1H = 1360; T1L=350; T0H=350; T0L=1360; Treset=50000 #APA106 timings
#timings = ((T1H,T1L), (T0H, T0L), Treset)
#pixels.timings(timings)
#pixels.color_order('RGB')
try:
	while True:
		print("Pixel to light:")
		led = int(input())
		pixels.fill((0, 0, 0))
		pixels[led] = (255, 255, 255)
		pixels.show()
except KeyboardInterrupt:
	pixels.fill((0, 0, 0))
	quit()
