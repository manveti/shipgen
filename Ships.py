import random

import Rooms

from Constants import *

TARGET_HEIGHT_FACTOR = 2.0 / 3
TARGET_LENGTH_FACTOR = 3
TARGET_WIDTH_FACTOR = 6.0 / (TARGET_HEIGHT_FACTOR * TARGET_LENGTH_FACTOR)


class Ship:
	def __init__(self):
		pass


def layoutShip(material, enclosure, symmetry, rooms, thrusters, gyros, reactors):
	# get non-empty, non-"Exterior" rooms; split into "bridge" (cockpit and possible windows) and non-"bridge" rooms
	bridgeRooms = []
	nonBridgeRooms = []
	partsVol = 0
	minHeight = 0
#####
##
#if symmetry enabled, add rooms in (pseudo-)symmetric pairs if possible; track pairs below
	for room in rooms.keys():
		if (room == Rooms.EXTERIOR):
			continue
		for roomParts in rooms[room]:
			if ((Rooms.rooms[room].windows > 0) and (roomParts.get("Cockpit", 0) > 0)):
				bridgeRooms.append((room, roomParts))
			elif (roomParts):
				nonBridgeRooms.append((room, roomParts))
			for part in roomParts.keys():
				partsVol += reduce(lambda x, y: x * y, Parts.parts[part].size, 1)
				partMin = min(Parts.parts[part].size)
				if (partMin > minHeight):
					minHeight = partMin
##
#####
	# determine target dimensions
	targetWidth = (partsVol * TARGET_WIDTH_FACTOR) ** (1.0 / 3)
	targetHeight = max(targetWidth * TARGET_HEIGHT_FACTOR, minHeight)
	targetLength = targetWidth * TARGET_LENGTH_FACTOR
	random.shuffle(bridgeRooms)
	random.shuffle(nonBridgeRooms)
#####
##
	#loop:
	#  grab next item from bridgeRooms + nonBridgeRooms
	#  generate room layout, handling (pseudo-)symmetric pairs appropriately
	#  if nothing placed yet: place front and center (possibly with a hallway between paired rooms)
	#  elif room(s) from bridgeRooms: place beside/above/below existing rooms
	#  else: place beside/behind/above/below existing rooms
	#add doorways/doors between rooms
	#add windows on outside faces
	#finish off hull (replace outer room walls with hull material if latter is stronger)
	#add "Exterior" parts
##
#####