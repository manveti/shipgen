import os.path

import ConfigFile
import Materials
import Parts

from Constants import *

MATERIALS = 'materials'
ENCLOSURE = 'enclosure'
DOORS = 'doors'
WINDOWS = 'windows'
FREE = 'free'
PARTS = 'parts'

DEFAULTS = {
	MATERIALS:	Materials.INTERIOR_DEFAULT,
	ENCLOSURE:	ENCLOSURE_FULL,
	DOORS:		.5,
	WINDOWS:	0,
}

EXTERIOR = "Exterior"
EXTERIOR_CONFIG = {
	MATERIALS:	{Materials.EXTERIOR_DEFAULT: 1},
	ENCLOSURE:	{ENCLOSURE_NONE: 1},
	DOORS:		0,
	WINDOWS:	0,
}
INTERIOR = "Interior"
INTERIOR_CONFIG = {
	MATERIALS:	{Materials.INTERIOR_DEFAULT: 1},
	ENCLOSURE:	{ENCLOSURE_NONE: 1},
	DOORS:		0,
	WINDOWS:	0,
}


initialized = False
rooms = {}


class Room:
	def __init__(self, roomName, configDict):
		if (TYPE_LG not in Parts.parts):
			raise Exception("No parts available for ship type %s" % TYPE_LG)

		self.name = roomName

		materialSum = 0
		self.materials = {}
		for material in configDict.get(MATERIALS, {}).keys():
			if (material not in Materials.materials):
#####
##
				#warn about unrecognized material
##
#####
				continue
			if (TYPE_LG not in Materials.materials[material].mass):
#####
##
				#warn about material with no large blocks
##
#####
				continue
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
		for encType in ENCLOSURE_SCALE:
			self.enclosure[encType] = float(configDict.get(ENCLOSURE, {}).get(encType, 0))
			enclosureSum += self.enclosure[encType]
		if (enclosureSum > 0):
			# normalize probabilities
			for encType in self.enclosure.keys():
				self.enclosure[encType] /= enclosureSum
		else:
			# no valid enclosure types; use default
			self.enclosure = {DEFAULTS[ENCLOSURE]: 1}

		self.doors = float(configDict.get(DOORS, DEFAULTS[DOORS]))
		self.windows = float(configDict.get(WINDOWS, DEFAULTS[WINDOWS]))

		self.free = {}
		freeConfig = [float(x) for x in configDict.get(FREE, "").split() if x]
		if ((len(freeConfig) > 0) and (freeConfig[0] > 0)):
			self.free[FREE_MIN] = freeConfig[0]
		else:
			self.free[FREE_MIN] = 0
		if ((len(freeConfig) > 1) and (freeConfig[1] >= self.free[FREE_MIN])):
			self.free[FREE_MAX] = freeConfig[1]
		else:
			self.free[FREE_MAX] = self.free[FREE_MIN]

		self.parts = {}
		for part in configDict.get(PARTS, {}).keys():
			if (part not in Parts.parts[TYPE_LG]):
#####
##
				#warn about unrecognized part
##
#####
				continue
			self.parts[part] = {}
			partConfig = [x for x in configDict[PARTS][part].split() if x]
			for key in [PART_MIN, PART_MAX]:
				if (partConfig):
					x = int(partConfig.pop(0))
					if (x >= 0):
						self.parts[part][key] = x


def init():
	global initialized
	if (initialized):
		return
	Materials.init()
	Parts.init()
	configPath = os.path.join(os.path.dirname(__file__), "data", "rooms.cfg")
	configDict = ConfigFile.readFile(configPath)
	rooms[EXTERIOR] = Room(EXTERIOR, EXTERIOR_CONFIG)
	rooms[INTERIOR] = Room(INTERIOR, INTERIOR_CONFIG)
	for roomName in configDict.keys():
		if (type(configDict[roomName]) != type({})):
			continue
		rooms[roomName] = Room(roomName, configDict[roomName])
	initialized = True
