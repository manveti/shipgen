import random

def randomDict(d):
	r = random.random()
	for k in d.keys():
		if (r < d[k]):
			return k
		r -= d[k]