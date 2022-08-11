import board
import neopixel
pixels = neopixel.NeoPixel(board.D21, 100, pixel_order=neopixel.RGB)
#T1H = 1360; T1L=350; T0H=350; T0L=1360; Treset=50000 #APA106 timings
#timings = ((T1H,T1L), (T0H, T0L), Treset)
#pixels.timings(timings)
#pixels.color_order('RGB')
pixels[0] = (255, 255, 255)
pixels.show()
