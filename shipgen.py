#!/usr/bin/env python

import sys

import Profiles


if (__name__ == "__main__"):
	if (len(sys.argv) > 1):
		ship = Profiles.generateShip(sys.argv[1])
	else:
		ship = Profiles.generateShip()
#####
##
	#do something with ship
##
#####