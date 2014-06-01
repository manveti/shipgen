import copy
import math
import random

import Materials
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

ENCLOSURE_DOOR_DIRECTIONS = {
	ENCLOSURE_PLATFORM:	set([DOWN]),
	ENCLOSURE_FULL:		set(ALL_DIRECTIONS),
}


def distSquared(p1, p2):
	retval = 0
	for i in xrange(min(len(p1), len(p2))):
		retval += (p1[i] - p2[i]) * (p1[i] - p2[i])
	return retval

def addList(l1, l2):
	return [l1[i] + l2[i] for i in xrange(min(len(l1), len(l2)))]

class Ship:
	def __init__(self, shipType, symmetry, targetSize):
		self.shipType = shipType
		self.size = TYPE_SIZES[self.shipType]
		self.symmetry = symmetry
		self.targetEdges = {PORT: int(-targetSize[0] / 2), SBD: int(targetSize[0] / 2),
							FWD: int(-targetSize[1] / 2), AFT: int(targetSize[1] / 2),
							UP: int(targetSize[2] / 2), DOWN: int(-targetSize[2] / 2)}
		self.occupied = {}
		self.parts = {}
		self.potentialDoorways = {}
		self.doorways = {}
		self.windows = set()
		self.structure = {}
		self.edges = set()
		self.structureMass = 0
		self.blocks = set()

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

	def addStructure(self, pos, material, block=Materials.BLOCK, alignment=None):
		(existingMaterial, existingBlock, existingAlignment) = self.structure.get(pos, (None, None, None))
		material = Materials.toughestMaterial(material, existingMaterial, self.size, block)
		if (block not in Materials.materials[material].toughness[self.size]):
			block = Materials.BLOCK
		self.structure[pos] = (material, block, alignment)
		self.edges.add(pos)

	def addRoom(self, room, partCounts, freeFactor, roomMaterial, roomEnclosure, roomName, isBridge):
#####
##
#handle symmetry and part rotation
		# determine room size and position
		roomSize = [1, 1, 1]
		roomVolume = 0
		for part in partCounts.keys():
			for i in xrange(len(roomSize)):
				if (Parts.parts[self.size][part].size[i] > roomSize[i]):
					roomSize[i] = Parts.parts[self.size][part].size[i]
			roomVolume += reduce(lambda x, y: x * y, Parts.parts[self.size][part].size, 1) * partCounts[part]
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
		if (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED]):
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
		else:
			self.edges.add((roomPos[0] + roomSize[0], roomPos[1] - 1, roomPos[2] + roomSize[2]))
			self.edges.add((roomPos[0] + roomSize[0], roomPos[1] + roomSize[1], roomPos[2] + roomSize[2]))
			self.edges.add((roomPos[0] - 1, roomPos[1] - 1, roomPos[2] + roomSize[2]))
			self.edges.add((roomPos[0] - 1, roomPos[1] + roomSize[1], roomPos[2] + roomSize[2]))
		if (roomEnclosure != ENCLOSURE_NONE):
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
		else:
			self.edges.add((roomPos[0] + roomSize[0], roomPos[1] - 1, roomPos[2] - 1))
			self.edges.add((roomPos[0] + roomSize[0], roomPos[1] + roomSize[1], roomPos[2] - 1))
			self.edges.add((roomPos[0] - 1, roomPos[1] - 1, roomPos[2] - 1))
			self.edges.add((roomPos[0] - 1, roomPos[1] + roomSize[1], roomPos[2] - 1))
		edgeRange = (min(roomPos), max(addList(roomPos, roomSize)) + 1)
		expandableSides = set(ALL_DIRECTIONS)
		incomingDoorways = {}
		incomingAccess = {}
		outgoingAccess = {}
		for i in xrange(*edgeRange):
			# edge blocks: add window if space is empty; remove is space is full
			if ((i >= roomPos[0]) and (i < roomPos[0] + roomSize[0])):
				if (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED]):
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
				else:
					self.edges.add((i, roomPos[1] - 1, roomPos[2] + roomSize[2]))
					self.edges.add((i, roomPos[1] + roomSize[1], roomPos[2] + roomSize[2]))
				if (roomEnclosure != ENCLOSURE_NONE):
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
				else:
					self.edges.add((i, roomPos[1] - 1, roomPos[2] - 1))
					self.edges.add((i, roomPos[1] + roomSize[1], roomPos[2] - 1))
			if ((i >= roomPos[1]) and (i < roomPos[1] + roomSize[1])):
				if (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED]):
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
				else:
					self.edges.add((roomPos[0] + roomSize[0], i, roomPos[2] + roomSize[2]))
					self.edges.add((roomPos[0] - 1, i, roomPos[2] + roomSize[2]))
				if (roomEnclosure != ENCLOSURE_NONE):
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
				else:
					self.edges.add((roomPos[0] + roomSize[0], i, roomPos[2] - 1))
					self.edges.add((roomPos[0] - 1, i, roomPos[2] - 1))
			if ((i >= roomPos[2]) and (i < roomPos[2] + roomSize[2])):
				if (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED]):
					blockPos = (roomPos[0] + roomSize[0], roomPos[1] + roomSize[1], i)
					if ((SBD in windowDirs) and (AFT in windowDirs) and (self.isFree(*blockPos))):
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
				else:
					self.edges.add((roomPos[0] + roomSize[0], roomPos[1] + roomSize[1], i))
					self.edges.add((roomPos[0] - 1, roomPos[1] + roomSize[1], i))
				if (roomEnclosure != ENCLOSURE_NONE):
					blockPos = (roomPos[0] + roomSize[0], roomPos[1] - 1, i)
					if ((SBD in windowDirs) and (FWD in windowDirs) and (self.isFree(*blockPos))):
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
				else:
					self.edges.add((roomPos[0] + roomSize[0], roomPos[1] - 1, i))
					self.edges.add((roomPos[0] - 1, roomPos[1] - 1, i))
			for j in xrange(*edgeRange):
				# face blocks: add window if space is empty; remove if space is full
				if ((i >= roomPos[0]) and (i < roomPos[0] + roomSize[0])):
					if ((j >= roomPos[1]) and (j < roomPos[1] + roomSize[1])):
						if (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED]):
							blockPos = (i, j, roomPos[2] + roomSize[2])
							if ((UP in windowDirs) and (self.isFree(*blockPos))):
								self.windows.add(blockPos)
							elif (blockPos in self.windows):
								self.windows.remove(blockPos)
							self.addStructure(blockPos, roomMaterial)
							if (self.isFree(*addList(blockPos, UP))):
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
						else:
							self.edges.add((i, j, roomPos[2] + roomSize[2]))
						if (roomEnclosure != ENCLOSURE_NONE):
							blockPos = (i, j, roomPos[2] - 1)
							if ((DOWN in windowDirs) and (self.isFree(*blockPos))):
								self.windows.add(blockPos)
							elif (blockPos in self.windows):
								self.windows.remove(blockPos)
							self.addStructure(blockPos, roomMaterial)
							if (self.isFree(*addList(blockPos, DOWN))):
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
						else:
							self.edges.add((i, j, roomPos[2] - 1))
					if ((j >= roomPos[2]) and (j < roomPos[2] + roomSize[2])):
						if (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED]):
							blockPos = (i, roomPos[1] - 1, j)
							if ((FWD in windowDirs) and (self.isFree(*blockPos))):
								self.windows.add(blockPos)
							elif (blockPos in self.windows):
								self.windows.remove(blockPos)
							self.addStructure(blockPos, roomMaterial)
							if (self.isFree(*addList(blockPos, FWD))):
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
							if (self.isFree(*addList(blockPos, AFT))):
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
						else:
							self.edges.add((i, roomPos[1] - 1, j))
							self.edges.add((i, roomPos[1] + roomSize[1], j))
				if ((i >= roomPos[1]) and (i < roomPos[1] + roomSize[1])):
					if ((j >= roomPos[2]) and (j < roomPos[2] + roomSize[2])):
						if (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED]):
							blockPos = (roomPos[0] + roomSize[0], i, j)
							if ((SBD in windowDirs) and (self.isFree(*blockPos))):
								self.windows.add(blockPos)
							elif (blockPos in self.windows):
								self.windows.remove(blockPos)
							self.addStructure(blockPos, roomMaterial)
							if (self.isFree(*addList(blockPos, SBD))):
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
							blockPos = (roomPos[0] - 1, i, j)
							if ((PORT in windowDirs) and (self.isFree(*blockPos))):
								self.windows.add(blockPos)
							elif (blockPos in self.windows):
								self.windows.remove(blockPos)
							self.addStructure(blockPos, roomMaterial)
							if (self.isFree(*addList(blockPos, PORT))):
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
						else:
							self.edges.add((roomPos[0] + roomSize[0], i, j))
							self.edges.add((roomPos[0] - 1, i, j))

		# require access to doors
		accessRequirements = {}
		for direction in ALL_DIRECTIONS:
			if (direction in incomingAccess):
				req = (1, incomingAccess[direction])
			else:
				req = (1, outgoingAccess.get(direction, []))
			if (req[1]):
				accessRequirements[id(req)] = req

		# place parts
		roomParts = {}
		occupied = set()
		accessReq = {}
		for part in reversed(sorted(partCounts.keys(), key=lambda p: reduce(lambda x, y: x * y, Parts.parts[self.size][p].size, 1))):
			partSize = Parts.parts[self.size][part].size
			partAccess = Parts.parts[self.size][part].accessRequirements
			for i in xrange(partCounts[part]):
				if (i > 0):
					partName = "%s %s %d" % (roomName, part, i)
				else:
					partName = "%s %s" % (roomName, part)
				while (True):
					bounds = [(roomPos[i], roomPos[i] + roomSize[i] + 1 - partSize[i]) for i in xrange(len(roomSize))]
					choices = set((x, y, z) for x in xrange(*bounds[0]) for y in xrange(*bounds[1]) for z in xrange(*bounds[2]))
					for (x, y, z) in occupied:
						for i in xrange(partSize[0]):
							for j in xrange(partSize[1]):
								for k in xrange(partSize[2]):
									pos = (x - i, y - j, z - k)
									if (pos in choices):
										choices.remove(pos)
#####
##
					#trim choices to remove places which don't fit partAccess
					#trim choices to remove places which prevent all access requirements from linking up
##
#####
					if (choices):
						partPos = random.choice(list(choices))
						partSpaces = set()
						for i in xrange(partSize[0]):
							for j in xrange(partSize[1]):
								for k in xrange(partSize[2]):
									pos = (partPos[0] + i, partPos[1] + j, partPos[2] + k)
									partSpaces.add(pos)
									occupied.add(pos)
						partAccessRequirements = {}
						for req in partAccess.values():
							reqPoints = set()
							for point in req[1]:
								reqPoints.add(tuple(addList(point, partPos)))
							accessSpec = (req[0], reqPoints)
							partAccessRequirements[id(accessSpec)] = accessSpec
							accessReq[id(accessSpec)] = accessSpec
						roomParts[partName] = (part, partPos, FWD, UP, partSpaces, partAccessRequirements)
						break
#####
##
					break
					#pick largest open space and try to move overlapping parts out of the way
					#if successful, pick appropriate partPos and repeat rest of "if (choices)" block above (including break)
					#pick random expandable direction; expand wall (retraverse expanded side as above)
##
#####
		# copy temporary parts dictionary into ship-wide one
		for partName in roomParts.keys():
			self.parts[partName] = roomParts[partName][:4]

		# turn potential incoming doorways into actual doorways
		roomDoorProb = Rooms.rooms[room].doors
		for direction in incomingAccess.keys():
			needDoor = (direction in ENCLOSURE_DOOR_DIRECTIONS.get(roomEnclosure, []))
			doorChoices = list(incomingAccess[direction])
			while (doorChoices):
				if (needDoor):
					accessBlock = doorChoices.pop(random.randrange(len(doorChoices)))
				else:
					accessBlock = doorChoices.pop(0)
				doorPos = incomingDoorways.get(accessBlock)
				if (doorPos in self.potentialDoorways):
					if (needDoor):
						doorProb = max(roomDoorProb, self.potentialDoorways[doorPos][1])
						self.doorways[doorPos] = (self.potentialDoorways[doorPos][0], doorProb)
						needDoor = False
					del self.potentialDoorways[doorPos]
##
#####

		# determine potential outgoing doorways
		edgeRange = (min(roomPos), max(addList(roomPos, roomSize)) + 1) # recompute; the room might have grown above
		for i in xrange(*edgeRange):
			for j in xrange(*edgeRange):
				if ((i >= roomPos[0]) and (i < roomPos[0] + roomSize[0])):
					if ((j >= roomPos[1]) and (j < roomPos[1] + roomSize[1])):
						doorPos = (i, j, roomPos[2] + roomSize[2])
						if ((self.isFree(*addList(doorPos, UP))) and (self.isFree(*addList(doorPos, DOWN)))):
							doorProb = max(roomDoorProb, self.potentialDoorways.get(doorPos, (0, 0))[1])
							self.potentialDoorways[doorPos] = (UP, doorProb)
						doorPos = (i, j, roomPos[2] - 1)
						if ((self.isFree(*addList(doorPos, DOWN))) and (self.isFree(*addList(doorPos, UP)))):
							doorProb = max(roomDoorProb, self.potentialDoorways.get(doorPos, (0, 0))[1])
							self.potentialDoorways[doorPos] = (DOWN, doorProb)
					if ((j >= roomPos[2]) and (j < roomPos[2] + roomSize[2]) and ((j & 1) == 0)):
						doorPos = (i, roomPos[1] - 1, j)
						if ((self.isFree(*addList(doorPos, FWD))) and (self.isFree(*addList(doorPos, AFT)))):
							doorProb = max(roomDoorProb, self.potentialDoorways.get(doorPos, (0, 0))[1])
							self.potentialDoorways[doorPos] = (FWD, doorProb)
						doorPos = (i, roomPos[1] + roomSize[1], j)
						if ((self.isFree(*addList(doorPos, AFT))) and (self.isFree(*addList(doorPos, FWD)))):
							doorProb = max(roomDoorProb, self.potentialDoorways.get(doorPos, (0, 0))[1])
							self.potentialDoorways[doorPos] = (AFT, doorProb)
				if ((i >= roomPos[1]) and (i < roomPos[1] + roomSize[1])):
					if ((j >= roomPos[2]) and (j < roomPos[2] + roomSize[2]) and ((j & 1) == 0)):
						doorPos = (roomPos[0] + roomSize[0], i, j)
						if ((self.isFree(*addList(doorPos, SBD))) and (self.isFree(*addList(doorPos, PORT)))):
							doorProb = max(roomDoorProb, self.potentialDoorways.get(doorPos, (0, 0))[1])
							self.potentialDoorways[doorPos] = (SBD, doorProb)
						doorPos = (roomPos[0] - 1, i, j)
						if ((self.isFree(*addList(doorPos, PORT))) and (self.isFree(*addList(doorPos, SBD)))):
							doorProb = max(roomDoorProb, self.potentialDoorways.get(doorPos, (0, 0))[1])
							self.potentialDoorways[doorPos] = (PORT, doorProb)

		# mark room spaces as occupied
		for x in xrange(roomPos[0] - 1, roomPos[0] + roomSize[0] + 1):
			if (x not in self.occupied):
				self.occupied[x] = {}
			for y in xrange(roomPos[1] - 1, roomPos[1] + roomSize[1] + 1):
				if (y not in self.occupied[x]):
					self.occupied[x][y] = set()
				self.occupied[x][y].update(xrange(roomPos[2] - 1, roomPos[2] + roomSize[2] + 1))

	def finalizeInterior(self, material, enclosure, doors):
		self.structureMass = 0
		self.blocks = set()

		if (enclosure == ENCLOSURE_FULL):
			# generate outgoing doorways
#####
##
#handle symmetry
#exclude windows
			potentialDirectionDoors = {}
			for doorPos in self.potentialDoorways.keys():
				(direction, doorProb) = self.potentialDoorways[doorPos]
				if (direction not in potentialDirectionDoors):
					potentialDirectionDoors[direction] = []
				potentialDirectionDoors[direction].append(doorPos)
			directions = [SBD, PORT]
			random.shuffle(directions)
			directions += [FWD, AFT, UP, DOWN]
			for direction in directions:
				if (doors <= 0):
					break
				if (direction not in potentialDirectionDoors):
					continue
				self.doorways[random.choice(potentialDirectionDoors[direction])] = (direction, 1)
				doors -= 1
##
#####

		# generate doors
		for doorPos in self.doorways.keys():
			# remove structure for doorway
			if (doorPos in self.structure):
				del self.structure[doorPos]
			if (doorPos in self.edges):
				self.edges.remove(doorPos)
			(direction, doorProb) = self.doorways[doorPos]
			if (random.random() < doorProb):
				self.blocks.add((Parts.DOOR, doorPos, direction))
				self.structureMass += Parts.parts[TYPE_LG][Parts.DOOR].mass

		# generate hull
		if (enclosure == ENCLOSURE_NONE):
			return
		for blockPos in self.edges:
			freeSides = set()
			for direction in ALL_DIRECTIONS:
				if (self.isFree(*addList(blockPos, direction))):
					freeSides.add(direction)
			if (not freeSides):
				# internal structure
				if (blockPos in self.structure):
					(blockMaterial, blockType, blockAlignment) = self.structure[blockPos]
					self.blocks.add((blockMaterial, blockPos, None))
					self.structureMass += Materials.materials[blockMaterial].mass[self.size][blockType]
				continue
			if ((enclosure == ENCLOSURE_PLATFORM) and (DOWN not in freeSides)):
				# wall or roof; not part of platform
				continue
			# determine if we can use a sloped block
			blockType = Materials.BLOCK
			blockAlignment = None
			if (UP in freeSides):
				if (SBD in freeSides):
					if (FWD in freeSides):
						blockType = Materials.CORNER
						blockAlignment = set([UP, SBD, FWD])
					elif (AFT in freeSides):
						blockType = Materials.CORNER
						blockAlignment = set([UP, SBD, AFT])
					else:
						blockType = Materials.SLOPE
						blockAlignment = set([UP, SBD])
				elif (PORT in freeSides):
					if (FWD in freeSides):
						blockType = Materials.CORNER
						blockAlignment = set([UP, PORT, FWD])
					elif (AFT in freeSides):
						blockType = Materials.CORNER
						blockAlignment = set([UP, PORT, AFT])
					else:
						blockType = Materials.SLOPE
						blockAlignment = set([UP, PORT])
				elif (FWD in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([UP, FWD])
				elif (AFT in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([UP, AFT])
				else:
					blockAlignment = set([UP])
			elif (DOWN in freeSides):
				if (SBD in freeSides):
					if (FWD in freeSides):
						blockType = Materials.CORNER
						blockAlignment = set([DOWN, SBD, FWD])
					elif (AFT in freeSides):
						blockType = Materials.CORNER
						blockAlignment = set([DOWN, SBD, AFT])
					else:
						blockType = Materials.SLOPE
						blockAlignment = set([DOWN, SBD])
				elif (PORT in freeSides):
					if (FWD in freeSides):
						blockType = Materials.CORNER
						blockAlignment = set([DOWN, PORT, FWD])
					elif (AFT in freeSides):
						blockType = Materials.CORNER
						blockAlignment = set([DOWN, PORT, AFT])
					else:
						blockType = Materials.SLOPE
						blockAlignment = set([DOWN, PORT])
				elif (FWD in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([DOWN, FWD])
				elif (AFT in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([DOWN, AFT])
				else:
					blockAlignment = set([DOWN])
			elif (SBD in freeSides):
				if (FWD in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([SBD, FWD])
				elif (AFT in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([SBD, AFT])
				else:
					blockAlignment = set([SBD])
			elif (PORT in freeSides):
				if (FWD in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([PORT, FWD])
				elif (AFT in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([PORT, AFT])
				else:
					blockAlignment = set([PORT])
			elif (FWD in freeSides):
				blockAlignment = set([FWD])
			elif (AFT in freeSides):
				blockAlignment = set([AFT])
			if (blockPos in self.windows):
#####
##
				pass
				#self.blocks.add((windowBlockName, blockPos, direction))
				#self.structureMass += windowMass
##
#####
			elif (blockPos not in self.doorways):
				self.addStructure(blockPos, material, blockType, blockAlignment)
				(blockMaterial, blockType, blockAlignment) = self.structure[blockPos]
				self.blocks.add((blockMaterial, blockPos, None))
				self.structureMass += Materials.materials[blockMaterial].mass[self.size][blockType]

	def finalizeParts(self):
#####
##
		pass
		#add everything in self.parts to self.blocks
##
#####

	def generateXML(self, entityId=None, pos=(0, 0, 0), fwd=(0, -1, 0), up=(0, 0, 1)):
		if (entityId is None):
#####
##
			entityId = 12345
##
#####
		retval = ['<MyObjectBuilder_EntityBase xsi:type="MyObjectBuilder_CubeGrid">',
					"  <EntityId>%s</EntityId>" % entityId,
					"  <PersistentFlags>CastShadows InScene</PersistentFlags>",
					"  <PositionAndOrientation>",
					'    <Position x="%s" y="%s" z="%s" />' % pos,
					'    <Forward x="%s" y="%s" z="%s" />' % fwd,
					'    <Up x="%s" y="%s" z="%s" />' % up,
					"  </PositionAndOrientation>"]
		if (self.size == TYPE_SM):
			retval.append("  <GridSizeEnum>Small</GridSizeEnum>")
		else:
			retval.append("  <GridSizeEnum>Large</GridSizeEnum>")
		entityId += 1
		retval.append("  <CubeBlocks>")
#####
##
		#blocks
##
#####
		retval.append("  </CubeBlocks>")
		if (self.shipType == TYPE_ST):
			retval.append("  <IsStatic>true</IsStatic>")
		else:
			retval.append("  <IsStatic>false</IsStatic>")
		retval.append("  <Skeleton />")
		retval.append('  <LinearVelocity x="0" y="0" z="0" />')
		retval.append('  <AngularVelocity x="0" y="0" z="0" />')
		retval.append('  <XMirroxPlane xsi:nil="true" />')
		retval.append('  <YMirroxPlane xsi:nil="true" />')
		retval.append('  <ZMirroxPlane xsi:nil="true" />')
		retval.append("  <ConveyorLines>")
#####
##
		#conveyor lines
##
#####
		retval.append("  </ConveyorLines>")
		retval.append("  <BlockGroups />")
		retval.append("</MyObjectBuilder_EntityBase>")
		return retval


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
			roomDict = random.choice(roomList)[0]
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
			rooms[Rooms.INTERIOR][0][0][part] = partCounts[part]

def layoutShip(shipType, material, enclosure, symmetry, rooms, thrusters, gyros, reactors, doors):
	size = TYPE_SIZES[shipType]
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
		i = 0
		for (roomDict, freeFactor, roomMaterial, roomEnclosure) in rooms[room]:
			if (not roomDict):
				continue
			if (i > 0):
				roomName = "%s %d" % (room, i)
			else:
				roomName = room
			i += 1
			if (freeFactor > 1):
				volFactor = float(freeFactor + 1) / 2
			else:
				volFactor = 1
			if ((Rooms.rooms[room].windows > 0) and (roomDict.get("Cockpit", 0) > 0)):
				bridgeRooms.append((room, roomDict, freeFactor, roomMaterial, roomEnclosure, roomName))
			else:
				nonBridgeRooms.append((room, roomDict, freeFactor, roomMaterial, roomEnclosure, roomName))
			for part in roomDict.keys():
				partsVol += reduce(lambda x, y: x * y, Parts.parts[size][part].size, volFactor) * roomDict[part]
				partMin = min(Parts.parts[size][part].size)
				if (partMin > minHeight):
					minHeight = partMin
##
#####
	# determine target dimensions
	targetWidth = (partsVol * TARGET_WIDTH_FACTOR) ** (1.0 / 3)
	targetHeight = max(targetWidth * TARGET_HEIGHT_FACTOR, minHeight)
	targetLength = targetWidth * TARGET_LENGTH_FACTOR
	# create ship; add rooms
	retval = Ship(shipType, symmetry, (targetWidth, targetLength, targetHeight))
	random.shuffle(bridgeRooms)
	random.shuffle(nonBridgeRooms)
	if (bridgeRooms):
		curRooms = bridgeRooms
		handlingBridge = True
	else:
		curRooms = nonBridgeRooms
		handlingBridge = False
	while (curRooms):
		(room, partCounts, freeFactor, roomMaterial, roomEnclosure, roomName) = curRooms.pop(0)
		retval.addRoom(room, partCounts, freeFactor, roomMaterial, roomEnclosure, roomName, handlingBridge)
		if ((handlingBridge) and (not curRooms)):
			curRooms = nonBridgeRooms
			handlingBridge = False
	# add hull, doors, and windows
	retval.finalizeInterior(material, enclosure, doors)
#####
##
	#add "Exterior" parts
##
#####
	retval.finalizeParts()
	return retval
