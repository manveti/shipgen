import os.path
import random

import ConfigFile
import Dists
import Parts
import Rooms
import Util

from Constants import *

MATERIALS = 'materials'
ENCLOSURE = 'enclosure'
ENCLOSURE_NONE = 'none'
ENCLOSURE_PLATFORM = 'platform'
ENCLOSURE_FULL = 'full'
ENCLOSURE_SEALED = 'sealed'
SYMMETRY = 'symmetry'
SYMMETRY_NONE = 'none'
SYMMETRY_PARTIAL = 'partial'
SYMMETRY_FULL = 'full'
ACCEL = 'accel'
ACCEL_MIN = 'min'
ACCEL_MAX = 'max'
ACCEL_FWD = 'fwd'
ACCEL_LAT = 'lat'
TURN = 'turn'
TURN_MIN = 'min'
TURN_MAX = 'max'
PARTS = 'parts'
PART_DISTRIBUTION = 'dist'
PART_MIN = 'min'
PART_MAX = 'max'
ROOMS = 'rooms'
ROOM_DISTRIBUTION = 'dist'
ROOM_MIN = 'min'
ROOM_MAX = 'max'

DEFAULTS = {
	MATERIALS:	"Light Armor",
	ENCLOSURE:	ENCLOSURE_FULL,
	SYMMETRY:	SYMMETRY_NONE,
	ACCEL:		{ACCEL_MIN: 1, ACCEL_MAX: 5, ACCEL_FWD: .5, ACCEL_LAT: .5},
	TURN:		{TURN_MIN: 1, TURN_MAX: 5},
}

initialized = False
classes = {}


class ShipClass:
	def __init__(self, shipType, configDict):
		self.shipType = shipType
		if (not Parts.parts.has_key(TYPE_SIZES[self.shipType])):
			raise Exception("No parts available for ship type %s" % self.shipType)

		materialSum = 0
		self.materials = {}
		for material in configDict.get(MATERIALS, {}).keys():
			self.materials[material] = float(configDict[MATERIALS][material])
			materialSum += self.materials[material]
		if (materialSum > 0):
			# normalize probabilities
			for material in self.materials.keys():
				self.materials[material] /= materialSum
		else:
			# no valid materials; use default
			self.materials = {DEFAULTS[MATERIALS]: 1}

		enclosureSum = 0
		self.enclosure = {}
		for encType in [ENCLOSURE_NONE, ENCLOSURE_PLATFORM, ENCLOSURE_FULL, ENCLOSURE_SEALED]:
			self.enclosure[encType] = float(configDict.get(ENCLOSURE, {}).get(encType, 0))
			enclosureSum += self.enclosure[encType]
		if (enclosureSum > 0):
			# normalize probabilities
			for encType in self.enclosure.keys():
				self.enclosure[encType] /= enclosureSum
		else:
			# no valid enclosure types; use default
			self.enclosure = {DEFAULTS[ENCLOSURE]: 1}

		symmetrySum = 0
		self.symmetry = {}
		for symType in [SYMMETRY_NONE, SYMMETRY_PARTIAL, SYMMETRY_FULL]:
			self.symmetry[symType] = float(configDict.get(SYMMETRY, {}).get(symType, 0))
			symmetrySum += self.symmetry[symType]
		if (symmetrySum > 0):
			# normalize probabilities
			for symType in self.symmetry.keys():
				self.symmetry[symType] /= symmetrySum
		else:
			# no valid symmetry types; use default
			self.symmetry = {DEFAULTS[SYMMETRY]: 1}

		self.accel = {}
		accelConfig = [float(x) for x in configDict.get(ACCEL, "").split() if x]
		for key in [ACCEL_MIN, ACCEL_MAX, ACCEL_FWD, ACCEL_LAT]:
			if (accelConfig):
				self.accel[key] = accelConfig.pop(0)
			else:
				self.accel[key] = DEFAULTS[ACCEL][key]
		if (self.accel[ACCEL_MIN] < 0):
			self.accel[ACCEL_MIN] = 0
		if (self.accel[ACCEL_MAX] < self.accel[ACCEL_MIN]):
			self.accel[ACCEL_MAX] = self.accel[ACCEL_MIN]
		if (self.accel[ACCEL_FWD] > 1):
			self.accel[ACCEL_FWD] = 1
		if (self.accel[ACCEL_LAT] > self.accel[ACCEL_FWD]):
			self.accel[ACCEL_LAT] = self.accel[ACCEL_FWD]

		self.turn = {}
		turnConfig = [float(x) for x in configDict.get(TURN, "").split() if x]
		for key in [TURN_MIN, TURN_MAX]:
			if (turnConfig):
				self.turn[key] = turnConfig.pop(0)
			else:
				self.turn[key] = DEFAULTS[TURN][key]
		if (self.turn[TURN_MIN] < 0):
			self.turn[TURN_MIN] = 0
		if (self.turn[TURN_MAX] < self.turn[TURN_MIN]):
			self.turn[TURN_MAX] = self.turn[TURN_MIN]

		self.parts = {}
		for part in configDict.get(PARTS, {}).keys():
			if (not Parts.parts[TYPE_SIZES[self.shipType]].has_key(part)):
#####
##
				#warn about unrecognized part
##
#####
				continue
			partConfig = configDict[PARTS][part]
			if (not partConfig):
				continue
			partDict = {}
			if (partConfig[0] == '"'):
				idx = partConfig.find('"', 1)
				if (idx > 0):
					partDict[PART_DISTRIBUTION] = partConfig[1 : idx]
					partConfig = partConfig[idx + 1:]
			partConfig = [x for x in partConfig.split() if x]
			if (not partDict.has_key(PART_DISTRIBUTION)):
				partDict[PART_DISTRIBUTION] = partConfig.pop(0)
			if (not Dists.dists.has_key(partDict[PART_DISTRIBUTION])):
#####
##
				#warn about unrecognized distribution
##
#####
				continue
			self.parts[part] = partDict
			for key in [PART_MIN, PART_MAX]:
				if (partConfig):
					x = int(partConfig.pop(0))
					if (x >= 0):
						self.parts[part][key] = x

		self.rooms = {}
		for room in configDict.get(ROOMS, {}).keys():
			if (not Rooms.rooms.has_key(room)):
#####
##
				#warn about unrecognized room
##
#####
				continue
			roomConfig = configDict[ROOMS][room]
			if (not roomConfig):
				continue
			roomDict = {}
			if (roomConfig[0] == '"'):
				idx = roomConfig.find('"', 1)
				if (idx > 0):
					roomDict[ROOM_DISTRIBUTION] = roomConfig[1 : idx]
					roomConfig = roomConfig[idx + 1:].strip()
			roomConfig = [x for x in roomConfig.split() if x]
			if (not roomDict.has_key(ROOM_DISTRIBUTION)):
				roomDict[ROOM_DISTRIBUTION] = roomConfig.pop(0)
			if (not Dists.dists.has_key(roomDict[ROOM_DISTRIBUTION])):
#####
##
				#warn about unrecognized distribution
##
#####
				continue
			self.rooms[room] = roomDict
			for key in [ROOM_MIN, ROOM_MAX]:
				if (roomConfig):
					x = int(roomConfig.pop(0))
					if (x >= 0):
						self.rooms[room][key] = x

	def fixCounts(self, partCounts, roomCounts):
		# first pass: each room individually
		partMins = {}
		for room in roomCounts.keys():
			for (part, partDict) in Rooms.rooms[room].parts.items():
				if ((roomCounts[room] * partDict[PART_MIN]) > partCounts.get(part, 0)):
					# reduce room count (to minimum of self.rooms[room][ROOM_MIN])
					roomCounts[room] = max(int(partCounts.get(part, 0) / partDict[PART_MIN]), self.rooms[room][ROOM_MIN])
				if ((roomCounts[room] * partDict[PART_MIN]) > partCounts.get(part, 0)):
					# increase part count (to maximum of self.parts[part][PART_MAX])
					partCounts[part] = min(roomCounts[room] * partDict[PART_MIN], self.parts[part][PART_MAX])
				if ((roomCounts[room] * partDict[PART_MIN]) > partCounts.get(part, 0)):
					# insufficient parts to meet room requirements; remove room
					roomCounts[room] = 0
					break
				partMins[part] = partMins.get(part, 0) + (roomCounts[room] * partDict[PART_MIN])

		# second pass: all rooms together
		for part in partMins.keys():
			tryReduce = True
			while ((partMins[part] > partCounts.get(part, 0)) and (tryReduce)):
				# reduce count of all affected rooms with count > self.rooms[room][ROOM_MIN]
				tryReduce = False
				for room in roomCounts.keys():
					if ((Rooms.rooms[room].parts.get(part, 0) > 0) and (roomCounts[room] > self.rooms[room][ROOM_MIN])):
						tryReduce = True
						roomCounts[room] -= 1
						for (roomPart, roomPartDict) in Rooms.rooms[room].parts.items():
							partMins[roomPart] -= roomPartDict[PART_MIN]
			if (partMins[part] > partCounts.get(part, 0)):
				# increase part count (to maximum of self.parts[part][PART_MAX])
				partCounts[part] = min(roomCounts[room] * partDict[PART_MIN], self.parts[part][PART_MAX])
			if (partMins[part] > partCounts.get(part, 0)):
				# insufficient parts to meet room requirements; remove highest-count room until requirements met
				affectedRooms = [(room, roomCounts[room] * Rooms.rooms[room].parts.get(part, 0)) for room in roomCounts.keys()]
				affectedRooms.sort(key=lambda t: t[1])
				while (partMins[part] > partCounts.get(part, 0)):
					(room, partCount) = affectedRooms.pop(0)
					for (roomPart, roomPartDict) in Rooms.rooms[room].parts.items():
						partMins[roomPart] -= roomPartDict[PART_MIN] * roomCounts[room]
					roomCounts[room] = 0

	def generateShip(self):
		material = Util.randomDict(self.materials)
		enclosure = Util.randomDict(self.enclosure)
		symmetry = Util.randomDict(self.symmetry)
		accel = random.uniform(self.accel[ACCEL_MIN], self.accel[ACCEL_MAX])
		accelFactorFwd = random.uniform(self.accel[ACCEL_FWD], 1)
		accelFactorLat = random.uniform(self.accel[ACCEL_LAT], accelFactorFwd)
		turn = random.uniform(self.turn[TURN_MIN], self.turn[TURN_MAX])
		partCounts = {}
		for part in self.parts.keys():
			n = Dists.dists[self.parts[part][PART_DISTRIBUTION]].getCount()
			if ((self.parts[part].has_key(PART_MIN)) and (n < self.parts[part][PART_MIN])):
				n = self.parts[part][PART_MIN]
			if ((self.parts[part].has_key(PART_MAX)) and (n > self.parts[part][PART_MAX])):
				n = self.parts[part][PART_MAX]
			if (n > 0):
				partCounts[part] = n
		roomCounts = {}
		for room in self.rooms.keys():
			n = Dists.dists[self.rooms[room][ROOM_DISTRIBUTION]].getCount()
			if ((self.rooms[room].has_key(ROOM_MIN)) and (n < self.rooms[room][ROOM_MIN])):
				n = self.rooms[room][ROOM_MIN]
			if ((self.rooms[room].has_key(ROOM_MAX)) and (n > self.rooms[room][ROOM_MAX])):
				n = self.rooms[room][ROOM_MAX]
			if (n > 0):
				roomCounts[room] = n
		self.fixCounts(partCounts, roomCounts)
#####
##
		#...
		print "material: %s"%material
		print "enclosure: %s"%enclosure
		print "symmetry: %s"%symmetry
		print "accel: %s (%s, %s)"%(accel,accelFactorFwd,accelFactorLat)
		print "turn: %s"%turn
		print "parts: %s"%partCounts
		print "rooms: %s"%roomCounts
##
#####


def init():
	global initialized
	if (initialized):
		return
	Dists.init()
	Parts.init()
	Rooms.init()
	for (shipType, typeAbbr) in TYPE_ABBRS.items():
		classes[shipType] = {}
		configPath = os.path.join(os.path.dirname(__file__), "data", "classes_%s.cfg" % typeAbbr)
		configDict = ConfigFile.readFile(configPath)
		for className in configDict.keys():
			if (type(configDict[className]) != type({})):
				continue
			classes[shipType][className] = ShipClass(shipType, configDict[className])
	initialized = True