#!/usr/bin/env python

import random

import Classes

from Common import *

initialized = False

def initialize():
	global initialized
	if (initialized):
		return
#####
##
	#load probability it distributions
##
#####
	Classes.initialize()
#####
##
	#other initialization
##
#####
	initialized = True

def generateShip(shipType=None):
	initialize()
	if (shipType is None):
		shipType = random.choice(TYPES)
	if (shipType not in TYPES):
		raise Exception("Invalid ship type: %s" % shipType)
#####
##
	#
##
#####


if (__name__ == "__main__"):
#####
##
	pass
	#invoke generator (possibly allow command-line arguments)
##
#####