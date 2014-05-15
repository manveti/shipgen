import os.path

import ConfigFile

from Constants import *

MASS = 'mass'
POWER = 'power'
SIZE = 'size'
ATTACHMENTS = 'attachments'
DOORS = 'doors'
ACCESS = 'access'
ROOMS = 'rooms'


initialized = False
parts = {}


class Part:
	def __init__(self, configDict):
		self.mass = float(configDict.get(MASS, 0))
		self.power = float(configDict.get(POWER, 0))

		self.size = [int(x) for x in configDict.get(SIZE, "").split() if x][:3]
		self.size += [1] * (3 - len(self.size))

#####
##
		#handle attachment points (ATTACHMENTS)
		#handle cargo doors (DOORS)
		#handle access requirements (ACCESS)
##
#####

		self.rooms = {}
		for room in configDict.get(ROOMS, {}).keys():
			self.rooms[room] = float(configDict[ROOMS][room])
		# no need to normalize room affinities now; we'll do it once we know which rooms a ship has


def init():
	global initialized
	if (initialized):
		return
	for size in SIZES:
		parts[size] = {}
		configPath = os.path.join("data", "parts_%s.cfg" % TYPE_ABBRS[size])
		configDict = ConfigFile.readFile(configPath)
		for partName in configDict.keys():
			if (type(configDict[partName]) != type({})):
				continue
			parts[size][partName] = Part(configDict[partName])
	initialized = True