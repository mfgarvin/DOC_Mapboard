import board
import neopixel
import math
import random
import time
import asyncio
import websockets

active = False
pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness=1)

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
  color = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
  for i in range(1,40):
    pixels.fill((color[0]*i/40, color[1]*i/40, color[2]*i/40))
  for i in range(1,40):
    i = abs(i-40)
    pixels.fill((color[0]*i/40, color[1]*i/40, color[2]*i/40))
  pixels.fill((0,0,0))

#Chase
async def chase():
  print("chase")
  library = [[255,0,0],[0,255,0],[0,0,255],[254,254,0],[255,255,255],[0,0,0]]
  for book in library:
    for i in range(400):
      if book[1] == 254:
        pixels[i] = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
      else:
        pixels[i] = (book[0], book[1], book[2])
    await asyncio.sleep(1)
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
  pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness=1, auto_write=False)
  for i in range (15):
    for i in range(400):
      pixels[i] = (random.randint(0,200), random.randint(0,200), random.randint(0,200))
    pixels.show()
    await asyncio.sleep(0.3)
    if active == False:
      break
  pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness=1)

async def alternate():
  iteration = 0
  print("alternate")
  colors = [[255,0,0],[255,127,0],[255,255,0],[127,255,0],[0,255,0],[0,255,127],[0,255,255],[0,127,255],[0,0,255],[127,0,255],[255,0,255],[255,255,255]]
  pixels = neopixel.NeoPixel(board.D21, 400, pixel_order=neopixel.RGB, brightness=1, auto_write=False)
  for i in range(16):
    pixels.fill((0,0,0))
    color_select=random.randint(0,11)
    for j in range(1,400):
      if iteration == 0 or iteration % 2 == 0:
        if j % 2 == 0:
          pixels[j] = (colors[color_select][0], colors[color_select][1], colors[color_select][2])
      else:
        if j % 2 != 0:
          pixels[j] = (colors[color_select][0], colors[color_select][1], colors[color_select][2])
    pixels.show()
    await asyncio.sleep(0.66)
    iteration = iteration + 1
    if active == False:
      break

asyncio.run(main())
#while True:
#  fade()
#  chase()
#  strobe()
#asyncio.run(alternate())



