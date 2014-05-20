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
SBD = (1, 0, 0)
PORT = (-1, 0, 0)
FWD = (0, -1, 0)
AFT = (0, 1, 0)


def addTuples(t1, t2):
	return tuple(t1[i] + t2[i] for i in xrange(min(len(t1), len(t2))))

class Ship:
	def __init__(self, targetSize):
		self.targetSize = targetSize
		self.targetEdges = {PORT: int(-targetSize[0] / 2), SBD: int(targetSize[0] / 2),
							FWD: int(-targetSize[1] / 2), AFT: int(targetSize[1] / 2),
							UP: int(targetSize[2] / 2), DOWN: int(-targetSize[2] / 2)}
		self.occupied = {}
		self.parts = {}
		self.potentialDoorways = set()
		self.doorways = set()

	def isFree(x0, y0, z0, w=1, l=1, h=1):
		for x in xrange(x0, x0 + w):
			if (x not in self.occupied):
				continue
			for y in xrange(y0, y0 + l):
				if (y not in self.occupied[x]):
					continue
				for z in xrange(z0, z0 + h):
					if (z in self.occupied[x][y]):
						return False
		return True

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
		if (not self.occupied):
			roomPos = [int(-roomSize[0] / 2), self.targetEdges[FWD], -2 * int(roomSize[2] / 4)]
		elif (isBridge):
			potentialPositions = set()
			minDSquared = None
			for (doorPos, direction) in self.potentialDoorways:
				y = max(self.targetEdges[FWD], doorPos[1] - roomSize[1])
				if (direction in [SBD, PORT]):
					if (direction == SBD):
						x = doorPos[0] + 1
						if (x + roomSize[0] > self.targetEdges[SBD]):
							continue
					else:
						x = doorPos[0] - roomSize[0]
						if (x < self.targetEdges[PORT]):
							continue
					bottom = doorPos[2]
					top = doorPos[2] - roomSize[2] + 1
					bottomDone = False
					topDone = False
					for i in xrange(roomSize[2] - 1):
						if ((not bottomDone) and (doorPos[2] - i >= self.targetEdges[DOWN])):
							if (self.isFree(x, y, doorPos[2] - i, roomSize[0], roomSize[1], 1)):
								bottom = doorPos[2] - i
							else:
								bottomDone = True
						if ((not topDone) and (doorPos[2] + i + roomSize[2] - 1 <= self.targetEdges[UP])):
							if (self.isFree(x, y, doorPos[2] + i, roomSize[0], roomSize[1], 1)):
								top = doorPos[2] + i
							else:
								topDone = True
						if ((bottomDone) and (topDone)):
							break
					if (bottom & 1):
						# make sure bottom is even (as doorPos[2] is)
						bottom += 1
					if (bottom >= top):
						continue
					z = min(abs(potentialZ) for potentialZ in xrange(bottom, top, 2))
					if (direction == SBD):
						dSquared = (doorPos[0] + 1) * (doorPos[0] + 1)
					else:
						dSquared = (doorPos[0] - 1) * (doorPos[0] - 1)
					dSquared += (y - self.targetEdges[FWD]) * (y - self.targetEdges[FWD])
					dSquared += (z + z + roomSize[2] - 1) * (z + z + roomSize[2] - 1) / 4
					potentialPositions.add(((x, y, z), dSquared))
					if ((minDSquared is None) or (dSquared < minDSquared)):
						minDSquared = dSquared
				elif (direction in [UP, DOWN]):
					if (direction == UP):
						z = doorPos[2] + 1
						if (z + roomSize[2] > self.targetEdges[UP]):
							continue
					else:
						z = doorPos[2] - roomSize[2]
						if (z < targetEdges[DOWN]):
							continue
					left = doorPos[0]
					right = doorPos[0] - roomSize[0] + 1
					leftDone = False
					rightDone = False
					for i in xrange(roomSize[0] - 1):
						if ((not leftDone) and (doorPos[0] - i >= self.targetEdges[LEFT])):
							if (self.isFree(doorPos[0] - i, y, z, 1, roomSize[1], roomSize[2])):
								left = doorPos[0] - i
							else:
								leftDone = True
						if ((not rightDone) and (doorPos[0] + i + roomSize[0] - 1 <= self.targetEdges[RIGHT])):
							if (self.isFree(doorPos[0] + i, y, z, 1, roomSize[1], roomSize[2])):
								right = doorPos[0] + i
							else:
								rightDone = True
						if ((leftDone) and (rightDone)):
							break
					if (left >= right):
						continue
					x = min(abs(potentialX) for potentialX in xrange(left, right))
					dSquared = float(x + x + roomSize[0] - 1) * float(x + x + roomSize[0] - 1) / 4
					if (direction == UP):
						dSquared += (doorPos[2] + 1) * (doorPos[2] + 1)
					else:
						dSquared += (doorPos[2] - 1) * (doorPos[2] - 1)
					dSquared += (y - self.targetEdges[FWD]) * (y - self.targetEdges[FWD])
					potentialPositions.add(((x, y, z), dSquared))
					if ((minDSquared is None) or (dSquared < minDSquared)):
						minDSquared = dSquared
				else:
					continue
			posChoices = [pos for (pos, dSquared) in potentialPositions if dSquared <= minDSquared]
#####
##
			#if not posChoices: posChoices = list of new position choices
##
#####
			roomPos = list(random.choice(posChoices))
		else:
#####
##
			#find closest point to (0,0,0) to place room
			#roomPos = somewhere adjacent to existing rooms (pick based on self.targetSize)
			pass
		#generate room layout, handling (pseudo-)symmetric pairs appropriately
		#  traverse reversed(sorted(partCounts.keys(), key=lambda p: tuple(reversed(Parts.parts[p].size)))) #g->l, h->l->w
		#  use roomSize to guide general layout
		#  make sure to leave freeVolume free space
		#  leave room to connect to existing rooms and to attachable sides as appropriate
		#update self.potentialDoorways and self.doorways so that only one doorway between rooms
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
	return retval
