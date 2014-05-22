import copy
import math
import random

import Parts
import Rooms
import Util

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
ALL_DIRECTIONS = [UP, DOWN, SBD, PORT, FWD, AFT]


def distSquared(p1, p2):
	retval = 0
	for i in xrange(min(len(p1), len(p2))):
		retval += (p1[i] - p2[i]) * (p1[i] - p2[i])
	return retval

def addList(l1, l2):
	return [l1[i] + l2[i] for i in xrange(min(len(l1), len(l2)))]

class Ship:
	def __init__(self, shipSize, targetSize):
		self.size = shipSize
		self.targetEdges = {PORT: int(-targetSize[0] / 2), SBD: int(targetSize[0] / 2),
							FWD: int(-targetSize[1] / 2), AFT: int(targetSize[1] / 2),
							UP: int(targetSize[2] / 2), DOWN: int(-targetSize[2] / 2)}
		self.occupied = {}
		self.parts = {}
		self.potentialDoorways = {}
		self.doorways = set()
		self.windows = set()
		self.structure = set()

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
			for doorPos in self.potentialDoorways.keys():
				(direction, doorProb) = self.potentialDoorways[doorPos]
				# one dimension is fixed based on position and alignment of doorway
				if (direction in [SBD, PORT]):
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
					tryPos = tuple(tryPosList.pop(0))
					obstruction = self.getObstruction(*(tryPos + tuple(roomSize)))
					if (obstruction is None):
						dSquared = distSquared(center, [float(tryPos[i] + roomSize[i]) / 2 for i in xrange(len(tryPos))])
						potentialPositions.add((tryPos, dSquared))
						if ((minDSquared is None) or (dSquared < minDSquared)):
							minDSquared = dSquared
					else:
						# obstruction prevents ideal placement, try moving away from center
						newTryPos = []
						for i in xrange(len(variableIdx)):
							p = list(tryPos)
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
			#try to find a position where a hall can be made from one of self.potentialDoorways
			#if potentialPositions: return best
##
#####
			# couldn't place room; expand self.targetEdges and try again
			for direction in self.targetEdges.keys():
				self.targetEdges[direction] += sum(direction)
##
#####

	def addStructure(self, pos, material):
#####
##
		#set material at pos to Materials.strongestMaterial(material, material already at pos)
##
#####
		self.structure.add(pos)

	def addRoom(self, room, partCounts, freeFactor, roomName, isBridge):
		roomMaterial = Util.randomDict(Rooms.rooms[room].materials)
#####
##
#handle symmetry and part rotation
		# determine room size and position
		roomSize = [1, 1, 1]
		roomVolume = 0
		for part in partCounts.keys():
			for i in xrange(len(roomSize)):
				if (Parts.parts[self.size][part].size[i] > roomSize[i]):
					roomSize[i] = Parts[part].size[i]
			roomVolume += reduce(lambda x, y: x * y, Parts.parts[self.size][part].size, 1)
		freeVolume = roomVolume * freeFactor
		roomVolume *= max(1 + freeFactor, 1.5)
		roomSize[2] |= 1 # ensure height is odd so room fits evenly into decks
		roomArea = float(roomVolume) / roomSize[2]
		roomSize[1] = max(int(math.ceil(math.sqrt(roomArea))), roomSize[1])
		roomSize[0] = max(int(math.ceil(roomArea / roomSize[1])), roomSize[0])
		roomPos = self.getRoomPos(roomSize, isBridge)

		# handle room edges (walls, windows, doorways)
		windowDirs = set()
		for direction in ALL_DIRECTIONS:
			if (random.random() < Rooms.rooms[room].windows):
				windowDirs.add(direction)
		# corner blocks: add window if space is empty; remove if space is full
		blockPos = (roomPos[0] + roomSize[0], roomPos[1] - 1, roomPos[2] + roomSize[2])
		if ((UP in windowDirs) and (SBD in windowDirs) and (FWD in windowDirs) and (self.isFree(*blockPos))):
			self.windows.add(blockPos)
		elif (blockPos in self.windows):
			self.windows.remove(blockPos)
		self.addStructure(blockPos, roomMaterial)
		blockPos = (roomPos[0] + roomSize[0], roomPos[1] + roomSize[1], roomPos[2] + roomSize[2])
		if ((UP in windowDirs) and (SBD in windowDirs) and (AFT in windowDirs) and (self.isFree(*blockPos))):
			self.windows.add(blockPos)
		elif (blockPos in self.windows):
			self.windows.remove(blockPos)
		self.addStructure(blockPos, roomMaterial)
		blockPos = (roomPos[0] - 1, roomPos[1] - 1, roomPos[2] + roomSize[2])
		if ((UP in windowDirs) and (PORT in windowDirs) and (FWD in windowDirs) and (self.isFree(*blockPos))):
			self.windows.add(blockPos)
		elif (blockPos in self.windows):
			self.windows.remove(blockPos)
		self.addStructure(blockPos, roomMaterial)
		blockPos = (roomPos[0] - 1, roomPos[1] + roomSize[1], roomPos[2] + roomSize[2])
		if ((UP in windowDirs) and (PORT in windowDirs) and (AFT in windowDirs) and (self.isFree(*blockPos))):
			self.windows.add(blockPos)
		elif (blockPos in self.windows):
			self.windows.remove(blockPos)
		self.addStructure(blockPos, roomMaterial)
		blockPos = (roomPos[0] + roomSize[0], roomPos[1] - 1, roomPos[2] - 1)
		if ((DOWN in windowDirs) and (SBD in windowDirs) and (FWD in windowDirs) and (self.isFree(*blockPos))):
			self.windows.add(blockPos)
		elif (blockPos in self.windows):
			self.windows.remove(blockPos)
		self.addStructure(blockPos, roomMaterial)
		blockPos = (roomPos[0] + roomSize[0], roomPos[1] + roomSize[1], roomPos[2] - 1)
		if ((DOWN in windowDirs) and (SBD in windowDirs) and (AFT in windowDirs) and (self.isFree(*blockPos))):
			self.windows.add(blockPos)
		elif (blockPos in self.windows):
			self.windows.remove(blockPos)
		self.addStructure(blockPos, roomMaterial)
		blockPos = (roomPos[0] - 1, roomPos[1] - 1, roomPos[2] - 1)
		if ((DOWN in windowDirs) and (PORT in windowDirs) and (FWD in windowDirs) and (self.isFree(*blockPos))):
			self.windows.add(blockPos)
		elif (blockPos in self.windows):
			self.windows.remove(blockPos)
		self.addStructure(blockPos, roomMaterial)
		blockPos = (roomPos[0] - 1, roomPos[1] + roomSize[1], roomPos[2] - 1)
		if ((DOWN in windowDirs) and (PORT in windowDirs) and (AFT in windowDirs) and (self.isFree(*blockPos))):
			self.windows.add(blockPos)
		elif (blockPos in self.windows):
			self.windows.remove(blockPos)
		self.addStructure(blockPos, roomMaterial)
		edgeRange = (min(roomPos), max(addList(roomPos, roomSize)) + 1)
		expandableSides = set(ALL_DIRECTIONS)
		incomingDoorways = {}
		incomingAccess = {}
		outgoingAccess = {}
		for i in xrange(*edgeRange):
			# edge blocks: add window if space is empty; remove is space is full
			if ((i >= roomPos[0]) and (i < roomPos[0] + roomSize[0])):
				blockPos = (i, roomPos[1] - 1, roomPos[2] + roomSize[2])
				if ((UP in windowDirs) and (FWD in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
				blockPos = (i, roomPos[1] + roomSize[1], roomPos[2] + roomSize[2])
				if ((UP in windowDirs) and (AFT in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
				blockPos = (i, roomPos[1] - 1, roomPos[2] - 1)
				if ((DOWN in windowDirs) and (FWD in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
				blockPos = (i, roomPos[1] + roomSize[1], roomPos[2] - 1)
				if ((DOWN in windowDirs) and (AFT in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
			if ((i >= roomPos[1]) and (i < roomPos[1] + roomSize[1])):
				blockPos = (roomPos[0] + roomSize[0], i, roomPos[2] + roomSize[2])
				if ((UP in windowDirs) and (SBD in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
				blockPos = (roomPos[0] - 1, i, roomPos[2] + roomSize[2])
				if ((UP in windowDirs) and (PORT in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
				blockPos = (roomPos[0] + roomSize[0], i, roomPos[2] - 1)
				if ((DOWN in windowDirs) and (SBD in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
				blockPos = (roomPos[0] - 1, i, roomPos[2] - 1)
				if ((DOWN in windowDirs) and (PORT in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
			if ((i >= roomPos[2]) and (i < roomPos[2] + roomSize[2])):
				blockPos = (roomPos[0] + roomSize[0], roomPos[1] - 1, i)
				if ((SBD in windowDirs) and (FWD in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
				blockPos = (roomPos[0] + roomSize[0], roomPos[1] + roomSize[1], i)
				if ((SBD in windowDirs) and (AFT in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
				blockPos = (roomPos[0] - 1, roomPos[1] - 1, i)
				if ((PORT in windowDirs) and (FWD in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
				blockPos = (roomPos[0] - 1, roomPos[1] + roomSize[1], i)
				if ((PORT in windowDirs) and (AFT in windowDirs) and (self.isFree(*blockPos))):
					self.windows.add(blockPos)
				elif (blockPos in self.windows):
					self.windows.remove(blockPos)
				self.addStructure(blockPos, roomMaterial)
			for j in xrange(*edgeRange):
				# face blocks: add window if space is empty; remove if space is full
				if ((i >= roomPos[0]) and (i < roomPos[0] + roomSize[0])):
					if ((j >= roomPos[1]) and (j < roomPos[1] + roomSize[1])):
						blockPos = (i, j, roomPos[2] + roomSize[2])
						if ((UP in windowDirs) and (self.isFree(*blockPos))):
							self.windows.add(blockPos)
						elif (blockPos in self.windows):
							self.windows.remove(blockPos)
						self.addStructure(blockPos, roomMaterial)
						if (self.getObstruction(*addList(blockPos, UP)) is None):
							if (UP not in outgoingAccess):
								outgoingAccess[UP] = set()
							outgoingAccess[UP].add(tuple(addList(blockPos, DOWN)))
						elif (UP in expandableSides):
							expandableSides.remove(UP)
						if (blockPos in self.potentialDoorways):
							if (UP not in incomingAccess):
								incomingAccess[UP] = set()
							accessBlock = tuple(addList(blockPos, DOWN))
							incomingAccess[UP].add(accessBlock)
							incomingDoorways[accessBlock] = blockPos
						blockPos = (i, j, roomPos[2] - 1)
						if ((DOWN in windowDirs) and (self.isFree(*blockPos))):
							self.windows.add(blockPos)
						elif (blockPos in self.windows):
							self.windows.remove(blockPos)
						self.addStructure(blockPos, roomMaterial)
						if (self.getObstruction(*addList(blockPos, DOWN)) is None):
							if (DOWN not in outgoingAccess):
								outgoingAccess[DOWN] = set()
							outgoingAccess[DOWN].add(tuple(addList(blockPos, UP)))
						elif (DOWN in expandableSides):
							expandableSides.remove(DOWN)
						if (blockPos in self.potentialDoorways):
							if (DOWN not in incomingAccess):
								incomingAccess[DOWN] = set()
							accessBlock = tuple(addList(blockPos, UP))
							incomingAccess[DOWN].add(accessBlock)
							incomingDoorways[accessBlock] = blockPos
					if ((j >= roomPos[2]) and (j < roomPos[2] + roomSize[2])):
						blockPos = (i, roomPos[1] - 1, j)
						if ((FWD in windowDirs) and (self.isFree(*blockPos))):
							self.windows.add(blockPos)
						elif (blockPos in self.windows):
							self.windows.remove(blockPos)
						self.addStructure(blockPos, roomMaterial)
						if (self.getObstruction(*addList(blockPos, FWD)) is None):
							if (FWD not in outgoingAccess):
								outgoingAccess[FWD] = set()
							outgoingAccess[FWD].add(tuple(addList(blockPos, AFT)))
						elif (FWD in expandableSides):
							expandableSides.remove(FWD)
						if (blockPos in self.potentialDoorways):
							if (FWD not in incomingAccess):
								incomingAccess[FWD] = set()
							accessBlock = tuple(addList(blockPos, AFT))
							incomingAccess[FWD].add(accessBlock)
							incomingDoorways[accessBlock] = blockPos
						blockPos = (i, roomPos[1] + roomSize[1], j)
						if ((AFT in windowDirs) and (self.isFree(*blockPos))):
							self.windows.add(blockPos)
						elif (blockPos in self.windows):
							self.windows.remove(blockPos)
						self.addStructure(blockPos, roomMaterial)
						if (self.getObstruction(*addList(blockPos, AFT)) is None):
							if (AFT not in outgoingAccess):
								outgoingAccess[AFT] = set()
							outgoingAccess[AFT].add(tuple(addList(blockPos, FWD)))
						elif (AFT in expandableSides):
							expandableSides.remove(AFT)
						if (blockPos in self.potentialDoorways):
							if (AFT not in incomingAccess):
								incomingAccess[AFT] = set()
							accessBlock = tuple(addList(blockPos, FWD))
							incomingAccess[AFT].add(accessBlock)
							incomingDoorways[accessBlock] = blockPos
				if ((i >= roomPos[1]) and (i < roomPos[1] + roomSize[1])):
					if ((j >= roomPos[2]) and (j < roomPos[2] + roomSize[2])):
						blockPos = (roomPos[0] - 1, i, j)
						if ((SBD in windowDirs) and (self.isFree(*blockPos))):
							self.windows.add(blockPos)
						elif (blockPos in self.windows):
							self.windows.remove(blockPos)
						self.addStructure(blockPos, roomMaterial)
						if (self.getObstruction(*addList(blockPos, SBD)) is None):
							if (SBD not in outgoingAccess):
								outgoingAccess[SBD] = set()
							outgoingAccess[SBD].add(tuple(addList(blockPos, PORT)))
						elif (SBD in expandableSides):
							expandableSides.remove(SBD)
						if (blockPos in self.potentialDoorways):
							if (SBD not in incomingAccess):
								incomingAccess[SBD] = set()
							accessBlock = tuple(addList(blockPos, PORT))
							incomingAccess[SBD].add(accessBlock)
							incomingDoorways[accessBlock] = blockPos
						blockPos = (roomPos[0] + roomSize[0], i, j)
						if ((PORT in windowDirs) and (self.isFree(*blockPos))):
							self.windows.add(blockPos)
						elif (blockPos in self.windows):
							self.windows.remove(blockPos)
						self.addStructure(blockPos, roomMaterial)
						if (self.getObstruction(*addList(blockPos, PORT)) is None):
							if (PORT not in outgoingAccess):
								outgoingAccess[PORT] = set()
							outgoingAccess[PORT].add(tuple(addList(blockPos, SBD)))
						elif (PORT in expandableSides):
							expandableSides.remove(PORT)
						if (blockPos in self.potentialDoorways):
							if (PORT not in incomingAccess):
								incomingAccess[PORT] = set()
							accessBlock = tuple(addList(blockPos, SBD))
							incomingAccess[PORT].add(accessBlock)
							incomingDoorways[accessBlock] = blockPos

		# require access to doors
		accessRequirements = {}
		for direction in ALL_DIRECTIONS:
			if (direction in incomingAccess):
				req = (1, incomingAccess[direction])
			else:
				req = (1, outgoingAccess.get(direction, []))
			if (req[1]):
				accessRequirements[id(req)] = req
#####
##
		#for part in partCounts.keys() sorted largest to smallest:
		#  #reversed(sorted(partCounts.keys(), key=lambda p: reduce(lambda x, y: x * y, Parts.parts[self.size][p].size, 1)))
		#  for i in xrange(partCounts[part]):
		#    pick a location for part
		#      if nowhere available, pick a random expandable direction and expand (retraverse expanded side as above)
		#    when key of incomingDoorways filled: del self.potentialDoorways[incomingDoorways[key]]; del incomingDoorways[key]
		#    make sure its access requirements are free and that all access requirements have paths to link up
		#      when only one path to link up access requirements, set all spaces in path as access requirements
		#    remove adjacent spaces from self.potentialDoorways (make sure we don't remove last one on a side)
		#      when potentialdoorways for a side reduced to one: add adjacent access space; add doorway to self.doorways
		#make sure we've added {doorPos: (direction, doorProbability)} to self.potentialDoorways
		doorPos = (roomPos[0] + roomSize[0] / 2, roomPos[1] + roomSize[1] / 2, roomPos[2] + roomSize[2])
		self.potentialDoorways[doorPos] = (UP, 0)
		doorPos = (roomPos[0] + roomSize[0] / 2, roomPos[1] + roomSize[1] / 2, roomPos[2] - 1)
		self.potentialDoorways[doorPos] = (DOWN, 0)
		doorPos = (roomPos[0] + roomSize[0], roomPos[1] + roomSize[1] / 2, roomPos[2] + roomSize[2] / 2)
		self.potentialDoorways[doorPos] = (SBD, 0)
		doorPos = (roomPos[0] - 1, roomPos[1] + roomSize[1] / 2, roomPos[2] + roomSize[2] / 2)
		self.potentialDoorways[doorPos] = (PORT, 0)
		doorPos = (roomPos[0] + roomSize[0] / 2, roomPos[1] - 1, roomPos[2] + roomSize[2] / 2)
		self.potentialDoorways[doorPos] = (FWD, 0)
		doorPos = (roomPos[0] + roomSize[0] / 2, roomPos[1] + roomSize[1], roomPos[2] + roomSize[2] / 2)
		self.potentialDoorways[doorPos] = (AFT, 0)
##
#####
		for x in xrange(roomPos[0] - 1, roomPos[0] + roomSize[0] + 1):
			if (x not in self.occupied):
				self.occupied[x] = {}
			for y in xrange(roomPos[1] - 1, roomPos[1] + roomSize[1] + 1):
				if (y not in self.occupied[x]):
					self.occupied[x][y] = set()
				self.occupied[x][y].update(xrange(roomPos[2] - 1, roomPos[2] + roomSize[2] + 1))
##
#####


def assignPartsToRooms(rooms, size, partCounts):
	for part in partCounts.keys():
		if (partCounts[part] <= 0):
			continue
		probSum = 0
		probDict = {}
		for (room, prob) in Parts.parts[size][part].rooms.items():
			if ((prob > 0) and (rooms.has_key(room))):
				probDict[room] = prob
				probSum += prob
		if (probSum > 0):
			# normalize probabilities
			for room in probDict.keys():
				probDict[room] /= probSum
		while ((probDict) and (partCounts[part] > 0)):
			room = Util.randomDict(probDict)
			maxCount = Rooms.rooms[room].parts.get(part, {}).get(PART_MAX)
			roomList = [r for r in rooms[room] if (maxCount is None) or (r.get(part, 0) < maxCount)]
			if (not roomList):
				# remove room from probDict, renormalizing first
				probSum = 1 - probDict[room]
				if (probSum <= 0):
					break
				for r in probDict.keys():
					probDict[r] /= probSum
				del probDict[room]
				continue
			roomDict = random.choice(roomList)
			roomDict[part] = roomDict.get(part, 0) + 1
			partCounts[part] -= 1
#####
##
	#balance rooms if symmetry requires it
##
#####
	# dump remaining unassigned parts into "Interior" pseudo-room
	for part in partCounts.keys():
		if (partCounts[part] > 0):
			rooms[Rooms.INTERIOR][0][part] = partCounts[part]

def layoutShip(size, material, enclosure, symmetry, rooms, thrusters, gyros, reactors):
	rooms = copy.deepcopy(rooms)
	# get non-empty, non-"Exterior" rooms; split into "bridge" (cockpit and possible windows) and non-"bridge" rooms
	bridgeRooms = []
	nonBridgeRooms = []
	partsVol = 0
	minHeight = 0
	# add gyros and reactors into rooms
	gyrosAndReactors = {}
	for gyro in gyros.keys():
		gyrosAndReactors[gyro.name] = gyros[gyro]
	for reactor in reactors.keys():
		gyrosAndReactors[reactor.name] = reactors[reactor]
	assignPartsToRooms(rooms, size, gyrosAndReactors)
#####
##
#if symmetry enabled, add rooms in (pseudo-)symmetric pairs if possible; track pairs below
	for room in rooms.keys():
		if (room == Rooms.EXTERIOR):
			continue
		freeRange = (Rooms.rooms[room].free[FREE_MIN], Rooms.rooms[room].free[FREE_MAX])
		i = 0
		for roomDict in rooms[room]:
			if (not roomDict):
				continue
			if (i > 0):
				roomName = "%s %d" % (room, i)
			else:
				roomName = room
			i += 1
			freeFactor = random.uniform(*freeRange)
			if (freeFactor > 1):
				volFactor = float(freeFactor + 1) / 2
			else:
				volFactor = 1
			if ((Rooms.rooms[room].windows > 0) and (roomDict.get("Cockpit", 0) > 0)):
				bridgeRooms.append((room, roomDict, freeFactor, roomName))
			else:
				nonBridgeRooms.append((room, roomDict, freeFactor, roomName))
			for part in roomDict.keys():
				partsVol += reduce(lambda x, y: x * y, Parts.parts[size][part].size, volFactor)
				partMin = min(Parts.parts[size][part].size)
				if (partMin > minHeight):
					minHeight = partMin
##
#####
	print "bridge rooms: %s"%bridgeRooms
	print "non-bridge rooms: %s"%nonBridgeRooms
	# determine target dimensions
	targetWidth = (partsVol * TARGET_WIDTH_FACTOR) ** (1.0 / 3)
	targetHeight = max(targetWidth * TARGET_HEIGHT_FACTOR, minHeight)
	targetLength = targetWidth * TARGET_LENGTH_FACTOR
	retval = Ship(size, (targetWidth, targetLength, targetHeight))
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
	#for all outer hull blocks:
	#  if (blockPos in retval.windows): place window
	#  else: retval.addStructure(blockPos, material)
	#add "Exterior" parts
##
#####
	return retval
