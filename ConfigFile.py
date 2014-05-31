try:
	from collections import OrderedDict
except ImportError:
	class OrderedDict(dict):
		def __init__(self, *args, **kwargs):
			dict.__init__(self)
			self.__keys = []
			self.update(*args, **kwargs)

		def __setitem__(self, key, value):
			if (key not in self):
				self.__keys.append(key)
			dict.__setitem__(self, key, value)

		def __delitem__(self, key):
			dict.__delitem__(self, key)
			self.__keys.remove(key)

		def __iter__(self):
			return self.__keys.__iter__()

		def __reversed__(self):
			return self.__keys.__reversed__()

		def clear(self):
			dict.clear(self)
			self.__keys = []

		def keys(self):
			return self.__keys[:]

		def values(self):
			return [self[key] for key in self.__keys]

		def items(self):
			return [(key, self[key]) for key in self.__keys]

		def iterkeys(self):
			return iter(self.__keys)

		def itervalues(self):
			for key in self.__keys:
				yield self[key]

		def iteritems(self):
			for key in self.__keys:
				yield (key, self[key])

		def update(*args, **kwargs):
			if (len(args) > 2):
				raise TypeError("update() takes at most 2 positional arguments (%s given)" % len(args))
			if (not args):
				raise TypeError("unbound method update() must be called with OrderedDict instance as first argument (got nothing instead)")
			# self folded into args so that we can handle 'self' keyword arg
			self = args[0]
			if (len(args) > 1):
				if (hasattr(args[1], 'keys')):
					for key in args[1].keys():
						self[key] = args[1][key]
				else:
					for (key, value) in args[1]:
						self[key] = value
			for key in kwargs.keys():
				self[key] = kwargs[key]


def readItem(f, inList=False):
	while (True):
		line = f.readline()
		if (not line):
			return None
		line = line.strip()
		if ((not line) or (line[0] == "#")):
			continue
		if (line in ["}", "]"]):
			return None
		if (inList):
			return line.strip()
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
		elif (value == "["):
			value = []
			while (True):
				item = readItem(f, True)
				if (not item):
					break
				value.append(item)
		return (key, value)

def readFile(fname):
	retval = OrderedDict()
	f = open(fname, "r")
	try:
		while (True):
			item = readItem(f)
			if (not item):
				return retval
			retval[item[0]] = item[1]
	finally:
		f.close()
