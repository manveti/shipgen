def readItem(f):
	while (True):
		line = f.readline()
		if (not line):
			return None
		line = line.strip()
		if ((not line) or (line[0] == "#")):
			continue
		if (line == "}"):
			return None
		splits = line.rsplit(":", 1)
		if (len(splits) < 2):
			raise Exception("Illegal config file line: %s" % line)
		key = splits[0].strip()
		value = splits[1].strip()
		if (value == "{"):
			value = {}
			while (True):
				item = readItem(f)
				if (not item):
					break
				value[item[0]] = item[1]
		return (key, value)

def readFile(fname):
	retval = {}
	f = open(fname, "r")
	try:
		while (True):
			item = readItem(f)
			if (not item):
				return retval
			retval[item[0]] = item[1]
	finally:
		f.close()