import os.path
import xml.etree.ElementTree


#####
##
dataDir = r'c:\program files (x86)\steam\steamapps\common\spaceengineers\content\data'
compFile = os.path.join(dataDir,'components.sbc')
blockFile = os.path.join(dataDir,'cubeblocks.sbc')
##
#####
def getComponents(fname):
	retval = {}
	tree = xml.etree.ElementTree.parse(fname)
	components = tree.getroot().find('Components')
	if (components is None):
#####
##
		print "Failed to parse components file %s" % fname
		return None
	for component in components.findall('Component'):
		compIdNode = component.find('Id')
		if (compIdNode is None):
			msg = "Unable to determine component id: no Id node"
			dn = component.find('DisplayName')
			if ((dn is not None) and (dn.text)):
				msg += " (DisplayName: %s)" % dn.text
			print msg
			continue
		compId = compIdNode.find('SubtypeId')
		if ((compId is None) or (not compId.text)):
			msg = "Unable to determine component id: no SubtypeId node"
			dn = component.find('DisplayName')
			if ((dn is not None) and (dn.text)):
				msg += " (DisplayName: %s)" % dn.text
			print msg
			continue
		compMass = component.find('Mass')
		if ((compMass is None) or (not compMass.text)):
			print "Unable to determine component (%s) mass" % compId.text
			continue
		try:
			retval[compId.text] = float(compMass.text)
		except ValueError:
			print "Invalid component (%s) mass: %s" % (compId.text, compMass.text)
##
#####
			continue
	return retval

def getBlocks(fname, components=None):
	retval = {}
	if (type(components) != type({})):
		if (components is None):
			components = os.path.join(os.path.dirname(fname), "Components.sbc")
		components = getComponents(components)
	if (not components):
#####
##
		print "Components required to load blocks"
		return None
	tree = xml.etree.ElementTree.parse(fname)
	definitions = tree.getroot().find('Definitions')
	if (definitions is None):
		print "Failed to parse blocks file %s" % fname
		return None
	for definition in definitions.findall('Definition'):
		block = {}

		publicNode = definition.find('Public')
		if ((publicNode is not None) and (publicNode.text.lower() != "true")):
			continue

		idNode = definition.find('Id')
		if (idNode is None):
			msg = "Unable to determine block id: no Id node"
			dn = definition.find('DisplayName')
			if ((dn is not None) and (dn.text)):
				msg += " (DisplayName: %s)" % dn.text
			print msg
			continue
		blockId = idNode.find('SubtypeId')
		if ((blockId is None) or (not blockId.text)):
			msg = "Unable to determine block id: no SubtypeId node"
			dn = definition.find('DisplayName')
			if ((dn is not None) and (dn.text)):
				msg += " (DisplayName: %s)" % dn.text
			print msg
			continue
		blockType = definition.find('CubeSize')
		if ((blockType is None) or (not blockType.text)):
			print "Unable to determine block (%s) type" % blockId.text
			continue

		blockSize = definition.find('Size')
		if (blockSize is None):
			print "Unable to determine block (%s) size" % blockId.text
			continue
		valid = True
		block['size'] = []
		for dim in ['x', 'y', 'z']:
			if (dim in blockSize.attrib):
				block['size'].append(blockSize.attrib[dim])
			else:
				#warn: unable to determine block size
				valid = False
				break
		if (not valid):
			continue

		blockComponents = definition.find('Components')
		if (blockComponents is None):
			#warn: unable to determine block components
			continue
		block['mass'] = 0
		for comp in blockComponents.findall('Component'):
			compId = comp.attrib.get('Subtype')
			if (compId is None):
				#warn: unable to determine component id
				valid = False
				break
			if (compId not in components):
				#warn: unrecognized component
				valid = False
				break
			try:
				compCount = int(comp.attrib.get('Count', ""))
			except ValueError:
				#warn: unable to determine component count
				valid = False
				break
			block['mass'] += components[compId] * compCount
		if (not valid):
			continue

		block['power'] = 0
		for key in ['RequiredPowerInput', 'OperationalPowerConsumption', 'MaxPowerConsumption']:
			powerNode = definition.find(key)
			if ((powerNode is not None) and (powerNode.text)):
				try:
					block['power'] = float(powerNode.text) * 1000
				except ValueError:
					#warn: unable to determine power consumption
					valid = False
					break
		if (not valid):
			continue
		powerNode = definition.find('MaxPowerOutput')
		if ((powerNode is not None) and (powerNode.text)):
			try:
				block['power'] = -float(powerNode.text) * 1000
			except ValueError:
				#warn: unable to determine power generation
				continue

		blockClass = idNode.find('TypeId')
		if ((blockClass is not None) and (blockClass.text in ["Thrust", "Gyro"])):
			forceNode = definition.find('ForceMagnitude')
			if ((forceNode is None) or (not forceNode.text)):
				#warn: unable to determine thruster/gyro force
				continue
			try:
				blockForce = float(forceNode.text)
			except ValueError:
				#warn: unable to determine thruster/gyro force
##
#####
				continue
			if (blockClass.text == "Thrust"):
				block['thrust'] = blockForce
			elif (blockClass.text == "Gyro"):
				block['turn'] = blockForce

		if (blockType.text not in retval):
			retval[blockType.text] = {}
		retval[blockType.text][blockId.text] = block

	return retval
