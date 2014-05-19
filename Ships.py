import math
import random

import Parts
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
		freeRange = (Rooms.rooms[room].free[FREE_MIN], Rooms.rooms[room].free[FREE_MAX])
		for roomParts in rooms[room]:
			freeFactor = random.uniform(*freeRange)
			if (freeFactor > 1):
				volFactor = float(freeFactor + 1) / 2
			else:
				volFactor = 1
			if ((Rooms.rooms[room].windows > 0) and (roomParts.get("Cockpit", 0) > 0)):
				bridgeRooms.append((room, roomParts, freeFactor))
			elif (roomParts):
				nonBridgeRooms.append((room, roomParts, freeFactor))
			for part in roomParts.keys():
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
	random.shuffle(bridgeRooms)
	random.shuffle(nonBridgeRooms)
	if (bridgeRooms):
		curRooms = bridgeRooms
		handlingBridge = True
	else:
		curRooms = nonBridgeRooms
		handlingBridge = False
	while (curRooms):
		(room, partCounts, freeFactor) = curRooms.pop(0)
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
#####
##
		#if nothing placed yet: pick a spot front and center (possibly leaving room for hallway between paired rooms)
		#elif handlingBridge: pick a spot beside/above/below existing rooms
		#else: pick a spot behind/beside/above/below existing rooms
		#generate room layout, handling (pseudo-)symmetric pairs appropriately
		#  traverse reversed(sorted(partCounts.keys(), key=lambda p: tuple(reversed(Parts.parts[p].size)))) #g->l, h->l->w
		#  use roomSize to guide general layout
		#  make sure to leave freeVolume free space
		#  leave room to connect to existing rooms and to attachable sides as appropriate
##
#####
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