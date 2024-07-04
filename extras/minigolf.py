import board
import neopixel
import math
import random
import time
import asyncio
import websockets

active = False
pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness=0.4)
leds = [35, 37, 41, 44, 45, 46, 48, 50, 52, 61, 67, 77, 84, 90, 99, 100, 104, 108, 113, 117, 120, 121, 122, 124, 125, 128, 130, 133, 134, 136, 137, 138, 140, 141, 142, 143, 144, 145, 147, 149, 150, 152, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 212, 213, 215, 216, 217, 219, 221, 222, 223, 224, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 238, 239, 241, 243, 245, 246, 250, 252, 257, 265, 269, 274, 279, 283, 285, 288, 290, 294, 296, 299, 300, 302, 305, 308, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 325, 327, 329, 331, 333, 336, 337, 338, 340, 343, 346, 349, 353, 363, 369, 371, 374, 376, 377, 378, 379, 381, 382, 383, 384, 385, 386, 388, 389, 391, 392, 393, 395, 396, 398, 399]

async def echo(websocket):
    global active
    async for message in websocket:
        await websocket.send(message)
        print(message)
        if message == "Start":
            active = True
#            strobe()
        if message == "Stop":
            active = False

async def controller():
    print("Running!")
    global active
    active = True
    while True:
      if active == False:
        print(active)
        pixels.fill((0,0,0))
        await asyncio.sleep(1)
      if active == True:
        print(active)
        task = asyncio.create_task(mixitup())
        await asyncio.sleep(1)
        await task
#        time.sleep(1)

async def main():
    async with websockets.serve(echo, "192.168.25.5", 8765):
        task = asyncio.create_task(controller())
        await asyncio.Future()  # run forever

# Strobe to start
def strobe():
  for i in range(3):
    pixels.fill((100,100,100))
    time.sleep(0.1)
    pixels.fill((0,0,0))
    time.sleep(0.9)

#Then loop all of this

async def mixitup():
  choice = random.randint(1,4)
  if choice == 1:
    task = asyncio.create_task(fade())
    if active == True:
      await task
    else:
      task.cancel()
    #fade()
  if choice == 2:
    task = asyncio.create_task(chase())
    if active == True:
      await task
    else:
      task.cancel()
    #chase()
  if choice == 3:
    task = asyncio.create_task(fill())
    if active == True:
      await task
    else:
      task.cancel()
    #fill()
  if choice == 4:
    task = asyncio.create_task(alternate())
    if active == True:
      await task
    else:
      task.cancel()
    #alternate

#Fade in and out a random color, for maybe 30 seconds worth
async def fade():
  print("fade")
#  pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness=0.4)
  color = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
  for i in range(1,40):
    pixels.fill((int(color[0]*i/40), int(color[1]*i/40), int(color[2]*i/40)))
  for i in range(1,40):
    i = abs(i-40)
    pixels.fill((int(color[0]*i/40), int(color[1]*i/40), int(color[2]*i/40)))
  pixels.fill((0,0,0))

#Chase
async def chase():
  print("chase")
  library = [[255,0,0],[0,255,0],[0,0,255],[254,254,0],[255,255,255],[0,0,0],[0,150,150],[150,0,150],[150,0,255]]
  for book in library:
    for i in leds:
      if book[1] == 254:
        pixels[i] = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
      else:
        pixels[i] = (book[0], book[1], book[2])
      await asyncio.sleep(0.1)
    await asyncio.sleep(5)
    if active == False:
      break

#async def follow():
#  print("follow)"
#  for i in range(400):
#    color[i] = (random.randint(0,200), random.randint(0,200), random.randint(0,200))
#  for j in range(400):
#    pixel(j) = (color[j][0], color[j][1], color[j][2])
#    active = j-1
#    
async def fill():
  print("fill")
  pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness=0.4, auto_write=False)
  for i in range (15):
    for i in leds:
      pixels[i] = (random.randint(0,200), random.randint(0,200), random.randint(0,200))
    pixels.show()
    await asyncio.sleep(1)
    if active == False:
      break
  pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness=0.4)

async def alternate():
  iteration = 0
  print("alternate")
  colors = [[255,0,0],[255,127,0],[255,255,0],[127,255,0],[0,255,0],[0,255,127],[0,255,255],[0,127,255],[0,0,255],[127,0,255],[255,0,255],[255,255,255]]
  pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness=0.4, auto_write=False)
  for i in range(16):
    pixels.fill((0,0,0))
    color_select=random.randint(0,11)
    for j in leds:
      if iteration == 0 or iteration % 2 == 0:
        if j % 2 == 0:
          pixels[j] = (colors[color_select][0], colors[color_select][1], colors[color_select][2])
      else:
        if j % 2 != 0:
          pixels[j] = (colors[color_select][0], colors[color_select][1], colors[color_select][2])
    pixels.show()
    await asyncio.sleep(5.66)
    iteration = iteration + 1
    if active == False:
      break

asyncio.run(controller())
#while True:
#  fade()
#  chase()
#  strobe()
#asyncio.run(alternate())



