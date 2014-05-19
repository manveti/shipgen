import math
import random

import Parts
import Rooms

from Constants import *

TARGET_HEIGHT_FACTOR = 2.0 / 3
TARGET_LENGTH_FACTOR = 3
TARGET_WIDTH_FACTOR = 6.0 / (TARGET_HEIGHT_FACTOR * TARGET_LENGTH_FACTOR)

UP = (0, 0, 1)
DOWN = (0, 0, -1)
RIGHT = (1, 0, 0)
LEFT = (-1, 0, 0)
AFT = (0, 1, 0)
FWD = (0, -1, 0)


class Ship:
	def __init__(self, targetSize):
		self.targetSize = targetSize
		self.parts = {}

	def addRoom(self, room, partCounts, freeFactor, roomName, isBridge):
		roomSize = [1, 1, 1]
		roomVolume = 0
		for part in partCounts.keys():
			for i in xrange(len(roomSize)):
				if (Parts[part].size[i] > roomSize[i]):
					roomSize[i] = Parts[part].size[i]
			roomVolume += reduce(lambda x, y: x * y, Parts.parts[part].size, 1)
		freeVolume = roomVolume * freeFactor
		roomVolume *= max(1 + freeFactor, 1.5)
		roomSize[2] |= 1 # ensure height is odd so room fits evenly into decks
		roomArea = float(roomVolume) / roomSize[2]
		roomSize[1] = max(math.ceil(math.sqrt(roomArea)), roomSize[1])
		roomSize[0] = max(math.ceil(roomArea / roomSize[1]), roomSize[0])
		if (not self.parts):
			roomPos = [int(-coord / 2) for coord in roomSize]
		elif (isBridge):
#####
##
			#roomPos = somewhere beside/above/below existing stuff (roomPos[2]=int(-roomSize[2]/2); others can vary)
			pass
		else:
			#roomPos = somewhere adjacent to existing rooms (pick based on self.targetSize)
			pass
		#generate room layout, handling (pseudo-)symmetric pairs appropriately
		#  traverse reversed(sorted(partCounts.keys(), key=lambda p: tuple(reversed(Parts.parts[p].size)))) #g->l, h->l->w
		#  use roomSize to guide general layout
		#  make sure to leave freeVolume free space
		#  leave room to connect to existing rooms and to attachable sides as appropriate
		#update self.freeSpace to note removal of this
##
#####


def layoutShip(material, enclosure, symmetry, rooms, thrusters, gyros, reactors):
	# get non-empty, non-"Exterior" rooms; split into "bridge" (cockpit and possible windows) and non-"bridge" rooms
	bridgeRooms = []
	nonBridgeRooms = []
	partsVol = 0
	minHeight = 0
#####
##
	#add gyros and reactors into rooms
#if symmetry enabled, add rooms in (pseudo-)symmetric pairs if possible; track pairs below
	for room in rooms.keys():
		if (room == Rooms.EXTERIOR):
			continue
		freeRange = (Rooms.rooms[room].free[FREE_MIN], Rooms.rooms[room].free[FREE_MAX])
		for i in xrange(len(rooms[room])):
			if (i > 0):
				roomName = "%s %d" % (room, i)
			else:
				roomName = room
			freeFactor = random.uniform(*freeRange)
			if (freeFactor > 1):
				volFactor = float(freeFactor + 1) / 2
			else:
				volFactor = 1
			if ((Rooms.rooms[room].windows > 0) and (rooms[room][i].get("Cockpit", 0) > 0)):
				bridgeRooms.append((room, rooms[room][i], freeFactor, roomName))
			elif (rooms[room][i]):
				nonBridgeRooms.append((room, rooms[room][i], freeFactor, roomName))
			for part in rooms[room][i].keys():
				partsVol += reduce(lambda x, y: x * y, Parts.parts[part].size, volFactor)
				partMin = min(Parts.parts[part].size)
				if (partMin > minHeight):
					minHeight = partMin
##
#####
	# determine target dimensions
	targetWidth = (partsVol * TARGET_WIDTH_FACTOR) ** (1.0 / 3)
	targetHeight = max(targetWidth * TARGET_HEIGHT_FACTOR, minHeight)
	targetLength = targetWidth * TARGET_LENGTH_FACTOR
	retval = Ship((targetWidth, targetLength, targetHeight))
	random.shuffle(bridgeRooms)
	random.shuffle(nonBridgeRooms)
	if (bridgeRooms):
		curRooms = bridgeRooms
		handlingBridge = True
	else:
		curRooms = nonBridgeRooms
		handlingBridge = False
	while (curRooms):
		(room, partCounts, freeFactor, roomName) = curRooms.pop(0)
		retval.addRoom(room, partCounts, freeFactor, roomName, handlingBridge)
		if ((handlingBridge) and (not curRooms)):
			curRooms = nonBridgeRooms
			handlingBridge = False
#####
##
	#add doorways/doors between rooms
	#add windows on outside faces
	#finish off hull (replace outer room walls with hull material if latter is stronger)
	#add "Exterior" parts
##
#####