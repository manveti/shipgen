import os.path

import ConfigFile

from Constants import *

BLOCK = 'block'
SLOPE = 'slope'
CORNER = 'corner'

EXTERIOR_DEFAULT = "Light Armor"
EXTERIOR_CONFIG = {
	TYPE_SM: {
		BLOCK:	"1 2",
		SLOPE:	"1 2",
		CORNER:	"1 2",
	},
	TYPE_LG: {
		BLOCK:	"1 2",
		SLOPE:	"1 2",
		CORNER:	"1 2",
	},
}

INTERIOR_DEFAULT = "Interior Wall"
INTERIOR_CONFIG = {
	TYPE_LG: {
		BLOCK:	"1 1",
	},
}


initialized = False
materials = {}


class Material:
	def __init__(self, materialName, configDict):
		self.name = materialName

		self.mass = {}
		self.toughness = {}
		for size in SIZES:
			if (size in configDict):
				self.mass[size] = {}
				self.toughness[size] = {}
				for key in [BLOCK, SLOPE, CORNER]:
					if (key in configDict[size]):
						blockConfig = [float(x) for x in configDict[size].get(key, "").split() if x]
						if (blockConfig):
							if (size not in self.mass):
								self.mass[size] = {}
								self.toughness[size] = {}
							self.mass[size][key] = blockConfig.pop(0)
						if (blockConfig):
							self.toughness[size][key] = blockConfig.pop(0)
						elif (key in self.mass.get(size, {})):
							self.toughness[size][key] = self.mass[size][key]


def init():
	global initialized
	if (initialized):
		return
	configPath = os.path.join(os.path.dirname(__file__), "data", "materials.cfg")
	configDict = ConfigFile.readFile(configPath)
	materials[EXTERIOR_DEFAULT] = Material(EXTERIOR_DEFAULT, EXTERIOR_CONFIG)
	materials[INTERIOR_DEFAULT] = Material(INTERIOR_DEFAULT, INTERIOR_CONFIG)
	for materialName in configDict.keys():
		if (type(configDict[materialName]) != type({})):
			continue
		materials[materialName] = Material(materialName, configDict[materialName])
	initialized = True

def toughestMaterial(m1, m2, size=TYPE_LG, block=BLOCK):
	if ((m1 not in materials) or (size not in materials[m1].toughness)):
		return m2
	if ((m2 not in materials) or (size not in materials[m2].toughness)):
		return m1
	if (materials[m1].toughness.get(size, {}).get(block) >= materials[m2].toughness.get(size, {}).get(block)):
		return m1
	return m2
