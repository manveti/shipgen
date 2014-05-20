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


def distSquared(p1, p2):
	retval = 0
	for i in xrange(min(len(p1), len(p2))):
		retval += (p1[i] - p2[i]) * (p1[i] - p2[i])
	return retval

class Ship:
	def __init__(self, targetSize):
		self.targetEdges = {PORT: int(-targetSize[0] / 2), SBD: int(targetSize[0] / 2),
							FWD: int(-targetSize[1] / 2), AFT: int(targetSize[1] / 2),
							UP: int(targetSize[2] / 2), DOWN: int(-targetSize[2] / 2)}
		self.occupied = {}
		self.parts = {}
		self.potentialDoorways = set()
		self.doorways = set()

	def getObstruction(self, x0, y0, z0, w=1, l=1, h=1):
		for x in xrange(x0, x0 + w):
			if (x not in self.occupied):
				continue
			for y in xrange(y0, y0 + l):
				if (y not in self.occupied[x]):
					continue
				for z in xrange(z0, z0 + h):
					if (z in self.occupied[x][y]):
						return (x, y, z)
		return None

	def isFree(self, *args, **kwargs):
		return (self.getObstruction(*args, **kwargs) is None)

#####
##
#add handling for symmetry
	def getRoomPos(self, roomSize, isBridge):
		if (not self.occupied):
			return [int(-roomSize[0] / 2), self.targetEdges[FWD], -2 * int(roomSize[2] / 4)]
		if (isBridge):
			center = (0, self.targetEdges[FWD] * 2, 0) # ahead of the ship so we'll favor the front face
		else:
			center = (0, 0, 0)
		potentialPositions = set()
		while (not potentialPositions):
			minDSquared = None
			for (doorPos, direction) in self.potentialDoorways:
				# one dimension is fixed based on position and alignment of doorway
				if (direction in [SBD, PRT]):
					fixedIdx = 0
				elif (direction in [FWD, AFT]):
					fixedIdx = 1
				else:
					fixedIdx = 2
				fixedVal = doorPos[fixedIdx] + sum(direction)
				# search other two dimensions for closest open space to center
				variableIdx = [i for i in xrange(3) if i != fixedIdx]
				tryPos = [0, 0, 0]
				tryPos[fixedIdx] = fixedVal
				for i in xrange(len(variableIdx)):
					idealPos = center[variableIdx[i]] - int(roomSize[variableIdx[i]] / 2)
					minPos = doorPos[variableIdx[i]] - roomSize[variableIdx[i]]
					maxPos = doorPos[variableIdx[i]]
					tryPos[variableIdx[i]] = max(min(idealPos, maxPos), minPos)
				tryPosList = [tryPos]
				while (tryPosList):
					tryPos = tryPosList.pop(0)
					obstruction = self.getObstruction(*(tryPos + roomSize))
					if (obstruction is None):
						dSquared = distSquared(center, [float(tryPos[i] + roomSize[i]) / 2 for i in xrange(len(tryPos))])
						potentialPositions.add((tryPos, dSquared))
						if ((minDSquared is None) or (dSquared < minDSquared)):
							minDSquared = dSquared
						break
					# obstruction prevents ideal placement, try moving away from center
					newTryPos = []
					for i in xrange(len(variableIdx)):
						p = tryPos[:]
						if (doorPos[variableIdx[i]] > obstruction[variableIdx[i]]):
							p[variableIdx[i]] = obstruction[variableIdx[i]] + 1
						elif (doorPos[variableIdx[i]] < obstruction[variableIdx[i]]):
							p[variableIdx[i]] = obstruction[variableIdx[i]] - roomSize[variableIdx[i]]
						else:
							continue
						newTryPos.append(p)
					newTryPos.sort(key=lambda p: distSquared(p, center))
					tryPosList += newTryPos
			posChoices = [pos for (pos, dSquared) in potentialPositions if dSquared <= minDSquared]
			if (posChoices):
				return random.choice(posChoices)
#####
##
			#try to find a position where a hall can be made from one of self.potentialDoors
			#if potentialPositions: return best
##
#####
			# couldn't place room; expand self.targetEdges and try again
			for direction in self.targetEdges.keys():
				self.targetEdges[direction] += sum(direction)
##
#####

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
		roomPos = self.getRoomPos(roomSize, isBridge)
#####
##
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
