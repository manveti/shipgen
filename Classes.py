import ConfigFile

from Common import *

initialized = False
classes = {}

def initialize():
	global initialized
	if (initialized):
		return
#####
##
	#load classes[TYPE_??] from ConfigFile.readFile("data/classes_??.cfg")
##
#####
	initialized = True