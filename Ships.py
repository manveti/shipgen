import copy
import itertools
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

def subtractList(l1, l2):
	return [l1[i] - l2[i] for i in xrange(min(len(l1), len(l2)))]

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
		self.attachmentPoints = {}

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
		if (pos not in self.edges):
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
		for part in reversed(sorted(partCounts.keys(), key=lambda p: reduce(lambda x, y: x * y, Parts.parts[self.size][p].size, 1))):
			partSize = Parts.parts[self.size][part].size
			partAccess = Parts.parts[self.size][part].accessRequirements
			for i in xrange(partCounts[part]):
				if (i > 0):
					partName = "%s %s %d" % (roomName, part, i)
				else:
					partName = "%s %s" % (roomName, part)
				while (True):
					# consider all points far enough from a wall to fit part
					bounds = [(roomPos[i], roomPos[i] + roomSize[i] + 1 - partSize[i]) for i in xrange(len(roomSize))]
					choices = set((x, y, z) for x in xrange(*bounds[0]) for y in xrange(*bounds[1]) for z in xrange(*bounds[2]))
					# trim choices which intersect other parts
					for partPos in itertools.product(*[xrange(s) for s in partSize]):
						choices.difference_update([c for c in choices if tuple(addList(c, partPos)) in occupied])
					# trim choices which run afoul of part access requirements
					for (accessCount, accessPoints) in partAccess.values():
						freeCounts = {}
						for c in choices:
							freeCounts[c] = len([a for a in accessPoints if tuple(addList(a, c)) not in occupied])
						choices.difference_update([c for c in choices if freeCounts[c] < accessCount])
					# trim choices which run afoul of existing access requirements
					for (accessCount, accessPoints) in accessRequirements.values():
						freeCounts = {}
						for c in choices:
							freeCounts[c] = 0
							for p in accessPoints:
								if (p in occupied):
									continue
								for i in xrange(len(p)):
									if ((p[i] < c[i]) or (p[i] >= c[i] + roomSize[i])):
										freeCounts[c] += 1
										break
						choices.difference_update([c for c in choices if freeCounts[c] < accessCount])
					# trim choices which prevent all free space from linking up
					invalidChoices = set()
					for c in choices:
						# determine free blocks adjacent to part
						adjacent = set()
						for (x, y) in itertools.product(xrange(partSize[0]), xrange(partSize[1])):
							blockPos = tuple(addList(c, (x, y, -1)))
							if ((blockPos[2] >= roomPos[2]) and (blockPos not in occupied)):
								adjacent.add(blockPos)
							blockPos = tuple(addList(c, (x, y, partSize[2])))
							if ((blockPos[2] < roomPos[2] + roomSize[2]) and (blockPos not in occupied)):
								adjacent.add(blockPos)
						for (x, z) in itertools.product(xrange(partSize[0]), xrange(partSize[2])):
							blockPos = tuple(addList(c, (x, -1, z)))
							if ((blockPos[1] >= roomPos[1]) and (blockPos not in occupied)):
								adjacent.add(blockPos)
							blockPos = tuple(addList(c, (x, partSize[1], z)))
							if ((blockPos[1] < roomPos[1] + roomSize[1]) and (blockPos not in occupied)):
								adjacent.add(blockPos)
						for (y, z) in itertools.product(xrange(partSize[1]), xrange(partSize[2])):
							blockPos = tuple(addList(c, (-1, y, z)))
							if ((blockPos[0] >= roomPos[0]) and (blockPos not in occupied)):
								adjacent.add(blockPos)
							blockPos = tuple(addList(c, (partSize[0], y, z)))
							if ((blockPos[0] < roomPos[0] + roomSize[0]) and (blockPos not in occupied)):
								adjacent.add(blockPos)
						if (not adjacent):
							continue
						# determine contiguous free areas around each adjacent block, merging overlapping zones
						partBlocks = set(tuple(addList(c, p)) for p in itertools.product(*[xrange(s) for s in partSize]))
						zones = []
						while (adjacent):
							curZone = set()
							newBlocks = set([adjacent.pop()])
							while (newBlocks):
								blockPos = newBlocks.pop()
								curZone.add(blockPos)
								for offset in ALL_DIRECTIONS:
									newPos = tuple(addList(blockPos, offset))
									if ((newPos[0] < roomPos[0]) or (newPos[0] >= roomPos[0] + roomSize[0])):
										continue
									if ((newPos[1] < roomPos[1]) or (newPos[1] >= roomPos[1] + roomSize[1])):
										continue
									if ((newPos[2] < roomPos[2]) or (newPos[2] >= roomPos[2] + roomSize[2])):
										continue
									if ((newPos not in occupied) and (newPos not in partBlocks)):
										if (newPos in adjacent):
											adjacent.remove(newPos)
										if (newPos not in curZone):
											newBlocks.add(newPos)
							overlaps = [z for z in zones if z.intersection(curZone)]
							if (overlaps):
								for z in overlaps:
									curZone.union_update(z)
									zones.remove(z)
							zones.append(curZone)
						if (len(zones) > 1):
							# part breaks room into at least two disjoint zones
							invalidChoices.add(c)
					choices.difference_update(invalidChoices)
					if (choices):
						partPos = random.choice(list(choices))
						partSpaces = set()
						for partBlock in itertools.product(*[xrange(s) for s in partSize]):
							pos = tuple(addList(partPos, partBlock))
							partSpaces.add(pos)
							occupied.add(pos)
						partAccessRequirements = {}
						for req in partAccess.values():
							reqPoints = set()
							for point in req[1]:
								reqPoints.add(tuple(addList(point, partPos)))
							accessSpec = (req[0], reqPoints)
							partAccessRequirements[id(accessSpec)] = accessSpec
							accessRequirements[id(accessSpec)] = accessSpec
						roomParts[partName] = (part, partPos, FWD, UP, partSpaces, partAccessRequirements)
						break
#####
##
					#pick largest open space and try to move overlapping parts out of the way
					#if successful, pick appropriate partPos and repeat rest of "if (choices)" block above (including break)
##
#####
					# couldn't place part; expand room and try again
					canExpandX = (SBD in expandableSides) or (PORT in expandableSides)
					canExpandY = (FWD in expandableSides) or (AFT in expandableSides)
					if ((canExpandX) and ((roomSize[0] < roomSize[1]) or (not canExpandY))):
						expandChoices = list(expandableSides.intersection([SBD, PORT]))
						if (len(expandChoices) > 1):
							sbdDist = abs(roomPos[0])
							portDist = abs(roomPos[0] + roomSize[0] - 1)
							if (sbdDist < portDist):
								expandDir = SBD
							elif (portDist < sbdDist):
								expandDir = PORT
							else:
								expandDir = random.choice(expandChoices)
						else:
							expandDir = expandChoices[0]
					elif (canExpandY):
						expandChoices = list(expandableSides.intersection([FWD, AFT]))
						if (len(expandChoices) > 1):
							fwdDist = abs(roomPos[1])
							aftDist = abs(roomPos[1] + roomSize[1] - 1)
							if (fwdDist < aftDist):
								expandDir = FWD
							elif (aftDist < fwdDist):
								expandDir = AFT
							else:
								expandDir = random.choice(expandChoices)
						else:
							expandDir = expandChoices[0]
					elif (expandableSides):
						expandDir = random.choice(list(expandableSides))
					else:
#####
##
						#warn about failure to place part
						print "unable to place %s"%partName
##
#####
						break
#####
##
					print "expanding in direction %s"%(expandDir,)
					print "old room pos: %s, size: %s"%(roomPos,roomSize)
##
#####
					# remove access requirements associated with existing wall in direction of expansion
					for key in accessRequirements.keys():
						(count, reqs) = accessRequirements[key]
						if (count == 1):
							if (reqs in [incomingAccess.get(expandDir, []), outgoingAccess.get(expandDir, [])]):
								del accessRequirements[key]
					for access in incomingAccess.get(expandDir, []):
						if (access in incomingDoorways):
							del incomingDoorways[access]
					if (expandDir in incomingAccess):
						del incomingAccess[expandDir]
					if (expandDir in outgoingAccess):
						del outgoingAccess[expandDir]
					# remove existing wall in direction of expansion
					extents = []
					posList = []
					varCoords = []
					for i in xrange(len(expandDir)):
						if (expandDir[i] < 0):
							posList.append(roomPos[i] - 1)
							expandCoord = i
						elif (expandDir[i] > 0):
							posList.append(roomPos[i] + roomSize[i])
							expandCoord = i
						else:
							extents.append((roomPos[i], roomPos[i] + roomSize[i]))
							posList.append(0)
							varCoords.append(i)
#####
##
					foo=['x','y','z']
					print "deleting wall at %s=%s"%(foo[expandCoord],posList[expandCoord])
##
#####
					for p in itertools.product(*[xrange(*r) for r in extents]):
						for i in xrange(len(p)):
							posList[varCoords[i]] = p[i]
						blockPos = tuple(posList)
#####
##
						print "  deleting structure at %s"%(blockPos,)
##
#####
						if (blockPos in self.windows):
							self.windows.remove(blockPos)
						if (blockPos in self.structure):
							del self.structure[blockPos]
						if (blockPos in self.edges):
							self.edges.remove(blockPos)
					# fill in walls all the way around for vertical expansion, as we expand 2 blocks at a time for even decks
					if (expandDir in [UP, DOWN]):
						roomSize[2] += 1
						if (expandDir == UP):
							posList[2] += 1
						else:
							posList[2] -= 1
							roomPos = list(roomPos)
							roomPos[2] -= 1
							roomPos = tuple(roomPos)
						if (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED]):
							posList[0] = roomPos[0] + roomSize[0]
							posList[1] = roomPos[1] - 1
							blockPos = tuple(blockPos)
							if ((SBD in windowDirs) and (FWD in windowDirs) and (self.isFree(*blockPos))):
								self.windows.add(blockPos)
							elif (blockPos in self.windows):
								self.windows.remove(blockPos)
							self.addStructure(blockPos, roomMaterial)
							posList[1] = roomPos[1] + roomSize[1]
							blockPos = tuple(blockPos)
							if ((SBD in windowDirs) and (AFT in windowDirs) and (self.isFree(*blockPos))):
								self.windows.add(blockPos)
							elif (blockPos in self.windows):
								self.windows.remove(blockPos)
							self.addStructure(blockPos, roomMaterial)
							posList[0] = roomPos[0] - 1
							posList[1] = roomPos[1] - 1
							blockPos = tuple(blockPos)
							if ((PORT in windowDirs) and (FWD in windowDirs) and (self.isFree(*blockPos))):
								self.windows.add(blockPos)
							elif (blockPos in self.windows):
								self.windows.remove(blockPos)
							self.addStructure(blockPos, roomMaterial)
							posList[1] = roomPos[1] + roomSize[1]
							blockPos = tuple(blockPos)
							if ((PORT in windowDirs) and (AFT in windowDirs) and (self.isFree(*blockPos))):
								self.windows.add(blockPos)
							elif (blockPos in self.windows):
								self.windows.remove(blockPos)
							self.addStructure(blockPos, roomMaterial)
						else:
							self.edges.add((roomPos[0] + roomSize[0], roomPos[1] - 1, posList[2]))
							self.edges.add((roomPos[0] + roomSize[0], roomPos[1] + roomSize[1], posList[2]))
							self.edges.add((roomPos[0] - 1, roomPos[1] - 1, posList[2]))
							self.edges.add((roomPos[0] - 1, roomPos[1] + roomSize[1], posList[2]))
						for i in xrange(*extents[0]):
							posList[0] = i
							for (j, winD) in [(extents[1][0] - 1, FWD), (extents[1][1], AFT)]:
								posList[1] = j
								blockPos = tuple(blockPos)
								if (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED]):
									if ((winD in windowDirs) and (self.isFree(*blockPos))):
										self.windows.add(blockPos)
									elif (blockPos in self.windows):
										self.windows.remove(blockPos)
									self.addStructure(blockPos, roomMaterial)
								else:
									self.edges.add(blockPos)
						for i in xrange(*extents[1]):
							posList[1] = i
							for (j, winD) in [(extents[0][1], SBD), (extents[0][0] - 1, PORT)]:
								posList[0] = j
								blockPos = tuple(blockPos)
								if (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED]):
									if ((winD in windowDirs) and (self.isFree(*blockPos))):
										self.windows.add(blockPos)
									elif (blockPos in self.windows):
										self.windows.remove(blockPos)
									self.addStructure(blockPos, roomMaterial)
								else:
									self.edges.add(blockPos)
					# expand walls
					roomSize[expandCoord] += 1
					if (expandDir[expandCoord] < 0):
						roomPos = list(roomPos)
						roomPos[expandCoord] -= 1
						roomPos = tuple(roomPos)
#####
##
					print "new room pos: %s, size: %s"%(roomPos,roomSize)
##
#####
					posList[expandCoord] += expandDir[expandCoord]
					# fill in expanded corners
					posList[varCoords[1]] = extents[1][1]
					if ((expandDir == DOWN) or (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED])):
						if (expandDir in [UP, DOWN]):
							winD = [AFT]
						else:
							winD = [UP]
						posList[varCoords[0]] = extents[0][0] - 1
						if (expandDir in [SBD, PORT]):
							winD.append(FWD)
						else:
							winD.append(PORT)
						blockPos = tuple(posList)
#####
##
						print "  adding corner structure at %s"%(blockPos,)
##
#####
						if ((expandDir in windowDirs) and (winD[0] in windowDirs) and (winD[1] in windowDirs) and (self.isFree(*blockPos))):
							self.windows.add(blockPos)
						elif (blockPos in self.windows):
							self.windows.remove(blockPos)
						self.addStructure(blockPos, roomMaterial)
						posList[varCoords[0]] = extents[0][1]
						if (expandDir in [SBD, PORT]):
							winD.append(AFT)
						else:
							winD.append(SBD)
						blockPos = tuple(posList)
#####
##
						print "  adding corner structure at %s"%(blockPos,)
##
#####
						if ((expandDir in windowDirs) and (winD[0] in windowDirs) and (winD[1] in windowDirs) and (self.isFree(*blockPos))):
							self.windows.add(blockPos)
						elif (blockPos in self.windows):
							self.windows.remove(blockPos)
						self.addStructure(blockPos, roomMaterial)
					else:
						posList[varCoords[0]] = extents[0][0] - 1
						self.edges.add(tuple(posList))
						posList[varCoords[0]] = extents[0][1]
						self.edges.add(tuple(posList))
					posList[varCoords[1]] = extents[1][0] - 1
					if ((expandDir != UP) and (roomEnclosure != ENCLOSURE_NONE)):
						if (expandDir in [UP, DOWN]):
							winD = [FWD]
						else:
							winD = [DOWN]
						posList[varCoords[0]] = extents[0][0] - 1
						if (expandDir in [SBD, PORT]):
							winD.append(FWD)
						else:
							winD.append(PORT)
						blockPos = tuple(posList)
#####
##
						print "  adding corner structure at %s"%(blockPos,)
##
#####
						if ((expandDir in windowDirs) and (winD[0] in windowDirs) and (winD[1] in windowDirs) and (self.isFree(*blockPos))):
							self.windows.add(blockPos)
						elif (blockPos in self.windows):
							self.windows.remove(blockPos)
						self.addStructure(blockPos, roomMaterial)
						posList[varCoords[0]] = extents[0][1]
						if (expandDir in [SBD, PORT]):
							winD.append(AFT)
						else:
							winD.append(SBD)
						blockPos = tuple(posList)
#####
##
						print "  adding corner structure at %s"%(blockPos,)
##
#####
						if ((expandDir in windowDirs) and (winD[0] in windowDirs) and (winD[1] in windowDirs) and (self.isFree(*blockPos))):
							self.windows.add(blockPos)
						elif (blockPos in self.windows):
							self.windows.remove(blockPos)
						self.addStructure(blockPos, roomMaterial)
					else:
						posList[varCoords[0]] = extents[0][0] - 1
						self.edges.add(tuple(posList))
						posList[varCoords[0]] = extents[0][1]
						self.edges.add(tuple(posList))
					# fill in expanded edges
					enclosed = (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED])
					if (expandDir in [UP, DOWN]):
						edgeSpecs = [(extents[1][0] - 1, FWD), (extents[1][1], AFT)]
					else:
						edgeSpecs = [(extents[1][1], UP), (extents[1][0] - 1, DOWN)]
					for i in xrange(*extents[0]):
						posList[varCoords[0]] = i
						for (j, winD) in edgeSpecs:
							posList[varCoords[1]] = j
							blockPos = tuple(posList)
#####
##
							print "  adding edge structure at %s"%(blockPos,)
##
#####
							if ((enclosed) or ((roomEnclosure != ENCLOSURE_NONE) and (DOWN in [expandDir, winD]))):
								if ((expandDir in windowDirs) and (winD in windowDirs) and (self.isFree(*blockPos))):
									self.windows.add(blockPos)
								elif (blockPos in self.windows):
									self.windows.remove(blockPos)
								self.addStructure(blockPos, roomMaterial)
							else:
								self.edges.add(blockPos)
					if (expandDir in [UP, DOWN]):
						edgeSpecs = [(extents[0][1], SBD), (extents[0][0] - 1, PORT)]
					else:
						edgeSpecs = [(extents[0][1], UP), (extents[0][0] - 1, DOWN)]
					for i in xrange(*extents[1]):
						posList[varCoords[1]] = i
						for (j, winD) in edgeSpecs:
							posList[varCoords[0]] = j
							blockPos = tuple(posList)
#####
##
							print "  adding edge1 structure at %s"%(blockPos,)
##
#####
							if (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED]):
								if ((expandDir in windowDirs) and (winD in windowDirs) and (self.isFree(*blockPos))):
									self.windows.add(blockPos)
								elif (blockPos in self.windows):
									self.windows.remove(blockPos)
								self.addStructure(blockPos, roomMaterial)
							else:
								self.edges.add(blockPos)
					# fill in expanded walls
					enclosed = (roomEnclosure in [ENCLOSURE_FULL, ENCLOSURE_SEALED])
					if ((expandDir == DOWN) and (roomEnclosure != ENCLOSURE_NONE)):
						enclosed = True
#####
##
					foo=['x','y','z']
					print "adding wall at %s=%s (extents: %s)"%(foo[expandCoord],posList[expandCoord],extents)
##
#####
					for p in itertools.product(*[xrange(*r) for r in extents]):
						for i in xrange(len(p)):
							posList[varCoords[i]] = p[i]
						blockPos = tuple(posList)
#####
##
						print "  adding structure at %s"%(blockPos,)
##
#####
						if (enclosed):
							if ((expandDir in windowDirs) and (self.isFree(*blockPos))):
								self.windows.add(blockPos)
							elif (blockPos in self.windows):
								self.windows.remove(blockPos)
							self.addStructure(blockPos, roomMaterial)
							if (self.isFree(*addList(blockPos, expandDir))):
								if (expandDir not in outgoingAccess):
									outgoingAccess[expandDir] = set()
								outgoingAccess[expandDir].add(tuple(subtractList(blockPos, expandDir)))
							elif (expandDir in expandableSides):
								expandableSides.remove(expandDir)
							if (blockPos in self.potentialDoorways):
								if (expandDir not in incomingAccess):
									incomingAccess[expandDir] = set()
								accessBlock = tuple(subtractList(blockPos, expandDir))
								incomingAccess[expandDir].add(accessBlock)
								incomingDoorways[accessBlock] = blockPos
						else:
							self.edges.add(blockPos)
					# recompute door access
					req = None
					if (expandDir in incomingAccess):
						req = (1, incomingAccess[expandDir])
					elif (expandDir in outgoingAccess):
						req = (1, outgoingAccess[expandDir])
					if ((req) and (req[1])):
						accessRequirements[id(req)] = req
#####
##
					print "trying to place %s; expanded in direction %s"%(partName,expandDir)
##
#####
		# copy temporary parts dictionary into ship-wide one
		for partName in roomParts.keys():
			self.parts[partName] = roomParts[partName][:4]

		# turn potential incoming doorways into actual doorways
		roomDoorProb = Rooms.rooms[room].doors
		for direction in incomingAccess.keys():
			needDoor = (direction in ENCLOSURE_DOOR_DIRECTIONS.get(roomEnclosure, []))
			doorChoices = [pos for pos in incomingAccess[direction] if pos not in occupied]
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
						if ((self.isFree(*addList(doorPos, UP))) and (tuple(addList(doorPos, DOWN)) not in occupied)):
							doorProb = max(roomDoorProb, self.potentialDoorways.get(doorPos, (0, 0))[1])
							self.potentialDoorways[doorPos] = (UP, doorProb)
						doorPos = (i, j, roomPos[2] - 1)
						if ((self.isFree(*addList(doorPos, DOWN))) and (tuple(addList(doorPos, UP)) not in occupied)):
							doorProb = max(roomDoorProb, self.potentialDoorways.get(doorPos, (0, 0))[1])
							self.potentialDoorways[doorPos] = (DOWN, doorProb)
					if ((j >= roomPos[2]) and (j < roomPos[2] + roomSize[2]) and ((j & 1) == 0)):
						doorPos = (i, roomPos[1] - 1, j)
						if ((self.isFree(*addList(doorPos, FWD))) and (tuple(addList(doorPos, AFT)) not in occupied)):
							doorProb = max(roomDoorProb, self.potentialDoorways.get(doorPos, (0, 0))[1])
							self.potentialDoorways[doorPos] = (FWD, doorProb)
						doorPos = (i, roomPos[1] + roomSize[1], j)
						if ((self.isFree(*addList(doorPos, AFT))) and (tuple(addList(doorPos, FWD)) not in occupied)):
							doorProb = max(roomDoorProb, self.potentialDoorways.get(doorPos, (0, 0))[1])
							self.potentialDoorways[doorPos] = (AFT, doorProb)
				if ((i >= roomPos[1]) and (i < roomPos[1] + roomSize[1])):
					if ((j >= roomPos[2]) and (j < roomPos[2] + roomSize[2]) and ((j & 1) == 0)):
						doorPos = (roomPos[0] + roomSize[0], i, j)
						if ((self.isFree(*addList(doorPos, SBD))) and (tuple(addList(doorPos, PORT)) not in occupied)):
							doorProb = max(roomDoorProb, self.potentialDoorways.get(doorPos, (0, 0))[1])
							self.potentialDoorways[doorPos] = (SBD, doorProb)
						doorPos = (roomPos[0] - 1, i, j)
						if ((self.isFree(*addList(doorPos, PORT))) and (tuple(addList(doorPos, SBD)) not in occupied)):
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
		self.attachmentPoints = {}

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
					if ((blockPos not in self.windows) and (blockPos not in self.doorways)):
						attachmentPos = tuple(addList(blockPos, UP))
						if (attachmentPos not in self.attachmentPoints):
							self.attachmentPoints[attachmentPos] = set()
						self.attachmentPoints[attachmentPos].add(UP)
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
					if ((blockPos not in self.windows) and (blockPos not in self.doorways)):
						attachmentPos = tuple(addList(blockPos, DOWN))
						if (attachmentPos not in self.attachmentPoints):
							self.attachmentPoints[attachmentPos] = set()
						self.attachmentPoints[attachmentPos].add(DOWN)
			elif (SBD in freeSides):
				if (FWD in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([SBD, FWD])
				elif (AFT in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([SBD, AFT])
				else:
					blockAlignment = set([SBD])
					if ((blockPos not in self.windows) and (blockPos not in self.doorways)):
						attachmentPos = tuple(addList(blockPos, SBD))
						if (attachmentPos not in self.attachmentPoints):
							self.attachmentPoints[attachmentPos] = set()
						self.attachmentPoints[attachmentPos].add(SBD)
			elif (PORT in freeSides):
				if (FWD in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([PORT, FWD])
				elif (AFT in freeSides):
					blockType = Materials.SLOPE
					blockAlignment = set([PORT, AFT])
				else:
					blockAlignment = set([PORT])
					if ((blockPos not in self.windows) and (blockPos not in self.doorways)):
						attachmentPos = tuple(addList(blockPos, PORT))
						if (attachmentPos not in self.attachmentPoints):
							self.attachmentPoints[attachmentPos] = set()
						self.attachmentPoints[attachmentPos].add(PORT)
			elif (FWD in freeSides):
				blockAlignment = set([FWD])
				if ((blockPos not in self.windows) and (blockPos not in self.doorways)):
					attachmentPos = tuple(addList(blockPos, FWD))
					if (attachmentPos not in self.attachmentPoints):
						self.attachmentPoints[attachmentPos] = set()
					self.attachmentPoints[attachmentPos].add(FWD)
			elif (AFT in freeSides):
				blockAlignment = set([AFT])
				if ((blockPos not in self.windows) and (blockPos not in self.doorways)):
					attachmentPos = tuple(addList(blockPos, AFT))
					if (attachmentPos not in self.attachmentPoints):
						self.attachmentPoints[attachmentPos] = set()
					self.attachmentPoints[attachmentPos].add(AFT)
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
#####
##
				self.blocks.add((blockMaterial, blockPos, None))
##
#####
				self.structureMass += Materials.materials[blockMaterial].mass[self.size][blockType]

	def addExterior(self, partCounts):
#####
##
#handle part rotation and symmetry
		# determine available attachment points
		for partKey in self.parts:
			part = self.parts[partKey][0]
			for (attachmentPos, attachmentDir) in Parts.parts[self.size][part].attachments:
				attachmentPoint = tuple(addList(addList(self.parts[partKey][1], attachmentPos), attachmentDir))
				if (self.isFree(*attachmentPoint)):
					if (attachmentPoint not in self.attachmentPoints):
						self.attachmentPoints[attachmentPoint] = set()
					self.attachmentPoints[attachmentPoint].add(attachmentDir)
		# add parts from partCounts, starting with those with the most attachment points
		accessRequirements = {}
		for doorPos in self.doorways.keys():
			(direction, doorProb) = self.doorways[doorPos]
			doorPos = tuple(addList(doorPos, direction))
			if (self.isFree(*doorPos)):
				req = (1, set([doorPos]))
				accessRequirements[id(req)] = req
		for part in reversed(sorted(partCounts.keys(), key=lambda p: len(Parts.parts[self.size][p].attachments))):
			partSize = Parts.parts[self.size][part].size
			for i in xrange(partCounts[part]):
				if (i > 0):
					partName = "%s %s %d" % (Rooms.EXTERIOR, part, i)
				else:
					partName = "%s %s" % (Rooms.EXTERIOR, part)
				# select attachment point to maximize contact area while minimizing loss of new attachment points
				pointsByScore = {}
				for point in self.attachmentPoints.keys():
					for (attachment, attachmentDir) in Parts.parts[self.size][part].attachments:
						inverseDir = tuple(subtractList((0, 0, 0), attachmentDir))
						if (inverseDir not in self.attachmentPoints[point]):
							#skip attachment points which would require part rotation
							continue
						partPos = tuple(subtractList(point, attachment))
						# verify part can fit
						valid = True
						for blockPos in itertools.product(*[xrange(s) for s in partSize]):
							blockPos = tuple(addList(partPos, blockPos))
							if (not self.isFree(*blockPos)):
								valid = False
								break
						if (valid):
							# verify part's access requirements are met
							for (accessCount, accessPoints) in Parts.parts[self.size][part].accessRequirements.values():
								for accessPos in accessPoints:
									if (self.isFree(*addList(accessPos, partPos))):
										accessCount -= 1
										if (accessCount <= 0):
											break
								if (accessCount > 0):
									valid = False
									break
						if (valid):
							# verify part doesn't run afoul of existing access requirements
							for (accessCount, accessPoints) in accessRequirements.values():
								for p in accessPoints:
									if (not self.isFree(*p)):
										continue
									for i in xrange(len(p)):
										if ((p[i] < partPos[i]) or (p[i] >= partPos[i] + partSize[i])):
											accessCount -= 1
											break
									if (accessCount <= 0):
										break
								if (accessCount > 0):
									valid = False
									break
						if (not valid):
							continue
						pointScore = 0
#####
##
						#for each block adjacent to part: if not self.isFree(*block): pointScore += 1
						#for each attachment point in part: if not self.isFree(*ap): pointScore -= 1
##
#####
						if (pointScore not in pointsByScore):
							pointsByScore[pointScore] = []
						pointsByScore[pointScore].append(partPos)
				if (pointsByScore):
					partPos = random.choice(pointsByScore[max(pointsByScore.keys())])
				elif (self.occupied):
#####
##
					print "nowhere to place %s"%partName
					continue
##
#####
				else:
					partPos = (0, 0, 0)
				self.parts[partName] = (part, partPos, FWD, UP)
#####
##
				print "placed %s at %s"%(partName,partPos)
##
#####
				# mark part spaces as occupied
				for blockPos in itertools.product(*[xrange(s) for s in Parts.parts[self.size][part].size]):
					blockPos = tuple(addList(partPos, blockPos))
					if (blockPos[0] not in self.occupied):
						self.occupied[blockPos[0]] = {}
					if (blockPos[1] not in self.occupied[blockPos[0]]):
						self.occupied[blockPos[0]][blockPos[1]] = set()
					self.occupied[blockPos[0]][blockPos[1]].add(blockPos[2])
					if (blockPos in self.attachmentPoints):
						del self.attachmentPoints[blockPos]
				# add new attachment points
				for (attachmentPos, attachmentDir) in Parts.parts[self.size][part].attachments:
					attachmentPoint = tuple(addList(addList(partPos, attachmentPos), attachmentDir))
					if (self.isFree(*attachmentPoint)):
						if (attachmentPoint not in self.attachmentPoints):
							self.attachmentPoints[attachmentPoint] = set()
						self.attachmentPoints[attachmentPoint].add(attachmentDir)
				# add new access requirements
				for (accessCount, accessPoints) in Parts.parts[self.size][part].accessRequirements.values():
					newPoints = set(tuple(addList(partPos, p)) for p in accessPoints)
					req = (accessCount, newPoints)
					accessRequirements[id(req)] = req
##
#####

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
		for (blockName, blockPos, blockAlign) in self.blocks:
#####
##
			retval.append("    <MyObjectBuilder_CubeBlock>")
			retval.append("      <SubtypeName>%s</SubtypeName>" % blockName)
			retval.append('      <Min x="%s" y="%s" z="%s" />' % blockPos)
			if (blockAlign is None):
				fwd = FWD
				up = UP
			elif (blockAlign in SE_DIRECTIONS):
				fwd = SE_DIRECTIONS[blockAlign]
				if (blockAlign in [UP, DOWN]):
					up = SE_DIRECTIONS[FWD]
				else:
					up = SE_DIRECTIONS[UP]
			else:
				fwd = SE_DIRECTIONS[blockAlign][0]
				up = SE_DIRECTIONS[blockAlign][1]
			retval.append('      <BlockOrientation Forward="%s" Up="%s" />' % (fwd, up))
			retval.append('      <ColorMaskHSV x="0" y="-1" z="0" />')
			retval.append("    </MyObjectBuilder_CubeBlock>")
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
	# add exterior parts
	partCounts = {}
	exteriorRooms = rooms.get(Rooms.EXTERIOR, [])
	if (exteriorRooms):
		exteriorSpec = exteriorRooms[0]
		if (exteriorSpec):
			partCounts = exteriorSpec[0]
#####
##
#handle thrusters appropriately: should have forced alignment based on d
	for d in thrusters.keys(): #ACCEL, ACCEL_FWD, ACCEL_LAT
		for thruster in thrusters[d].keys():
			if (thruster.name not in partCounts):
				partCounts[thruster.name] = 0
			partCounts[thruster.name] += thrusters[d][thruster]
##
#####
	retval.addExterior(partCounts)
	# finalize ship
	retval.finalizeParts()
	return retval
