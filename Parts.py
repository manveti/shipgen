import os.path

import ConfigFile
import Rooms

from Constants import *

MASS = 'mass'
POWER = 'power'
THRUST = 'thrust'
TURN = 'turn'
SIZE = 'size'
ATTACHMENTS = 'attachments'
DOORS = 'doors'
ACCESS = 'access'
ROOMS = 'rooms'

DOOR  = "Door"
DOOR_CONFIG = {
	MASS:	"642.4",
	POWER:	"0.001",
	SIZE:	"1 1 1",
	ATTACHMENTS:	["0 0 1", "0 0 -1", "1 0 0", "-1 0 0"],
	ACCESS:	["0 1 0", "0 -1 0"],
}

PRIORITIZATION_MASS_FACTOR = .5


initialized = False
parts = {}
reactors = {}
thrusters = {}
gyros = {}


class Part:
	def __init__(self, partName, configDict):
		self.name = partName

		self.mass = float(configDict.get(MASS, 0))
		self.power = float(configDict.get(POWER, 0))
		self.thrust = float(configDict.get(THRUST, 0))
		self.turn = float(configDict.get(TURN, 0))

		self.size = [int(x) for x in configDict.get(SIZE, "").split() if x][:3]
		self.size += [1] * (3 - len(self.size))

#####
##
		#handle attachment points (ATTACHMENTS)
		#handle cargo doors (DOORS)
		#handle access requirements (ACCESS)
##
#####

		interiorProb = 1
		self.rooms = {}
		for room in configDict.get(ROOMS, {}).keys():
			self.rooms[room] = float(configDict[ROOMS][room])
			interiorProb -= self.rooms[room]
		# no need to normalize room affinities now; we'll do it once we know which rooms a ship has
		if ((interiorProb > 0) and (Rooms.INTERIOR not in self.rooms)):
			self.rooms[Rooms.INTERIOR] = interiorProb


def prioritizeByEfficiency(l):
	# return a list of components increasing in both mass and efficiency
	# result should be traversed until a part meets the requirements, yielding the lowest-mass, highest-efficiency part for the job
	retval = []
	l.sort(key=lambda t: t[1] / t[2])
	maxMass = None
	for t in l:
		if ((maxMass is None) or (t[2] < maxMass)):
			retval.append(t[0])
			maxMass = t[2] * PRIORITIZATION_MASS_FACTOR
	retval.reverse()
	return retval

def init():
	global initialized
	if (initialized):
		return
	for size in SIZES:
		parts[size] = {}
		if (size == TYPE_LG):
			parts[size][DOOR] = Part(DOOR, DOOR_CONFIG)
		configPath = os.path.join(os.path.dirname(__file__), "data", "parts_%s.cfg" % TYPE_ABBRS[size])
		configDict = ConfigFile.readFile(configPath)
		allReactors = []
		allThrusters = []
		allGyros = []
		for partName in configDict.keys():
			if (type(configDict[partName]) != type({})):
				continue
			parts[size][partName] = Part(partName, configDict[partName])
			if (parts[size][partName].mass != 0):
				if (parts[size][partName].power < 0):
					allReactors.append((parts[size][partName], -parts[size][partName].power, parts[size][partName].mass))
				if (parts[size][partName].thrust > 0):
					allThrusters.append((parts[size][partName], parts[size][partName].thrust, parts[size][partName].mass))
				if (parts[size][partName].turn > 0):
					allGyros.append((parts[size][partName], parts[size][partName].turn, parts[size][partName].mass))
		reactors[size] = prioritizeByEfficiency(allReactors)
		thrusters[size] = prioritizeByEfficiency(allThrusters)
		gyros[size] = prioritizeByEfficiency(allGyros)
	initialized = True
