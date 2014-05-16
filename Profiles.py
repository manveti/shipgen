import os.path
import random

import Classes
import ConfigFile
import Util

from Constants import *

initialized = False
profiles = {}

class Profile:
	def __init__(self, configDict):
		classSum = 0
		self.classes = {}
		for shipType in TYPES:
			if (shipType not in Classes.classes):
#####
##
				#warn about unrecognized ship type
##
#####
				continue
			for shipClass in configDict.get(shipType, {}).keys():
				if (shipClass not in Classes.classes[shipType]):
#####
##
					#warn about unrecognized ship class
##
#####
					continue
				self.classes[(shipType, shipClass)] = float(configDict[shipType][shipClass])
				classSum += self.classes[(shipType, shipClass)]
		if (classSum > 0):
			# normalize probabilities
			for key in self.classes.keys():
				self.classes[key] /= classSum
		else:
			# no valid ship classes
			self.classes = {}

	def generateShip(self):
		(shipType, shipClass) = Util.randomDict(self.classes)
		if (shipType not in Classes.classes):
			raise Exception("Unrecognized ship type: %s" % shipType)
		if (shipClass not in Classes.classes[shipType]):
			raise Exception("Unrecognized ship class: %s" % shipClass)
		return Classes.classes[shipType][shipClass].generateShip()


def init():
	global initialized
	if (initialized):
		return
	Classes.init()
	configPath = os.path.join(os.path.dirname(__file__), "data", "profiles.cfg")
	configDict = ConfigFile.readFile(configPath)
	for profName in configDict.keys():
		if (type(configDict[profName]) != type({})):
			continue
		profiles[profName] = Profile(configDict[profName])
	initialized = True

def generateShip(profile=None):
	init()
	if (profile is None):
		profile = random.choice(profiles.keys())
	if (profile not in profiles):
		raise Exception("Invalid profile: %s" % profile)
	return profiles[profile].generateShip()