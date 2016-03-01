#    Copyright 2016 Parinz Ameri, Haipeng Guan
#
#    This file is part of Nowog.
#
#    Nowog is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Nowog is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Nowog.  If not, see <http://www.gnu.org/licenses/>

"""Random values generator

This module generate random values for database operation. Types of random
values including random integer, string, boolean, float point, a dictionary
of random range in MongoDB (e.g. {"$gte": 0, "$lt": 10}), as well as random
array of integer, string, boolean, float point.Several internal parameters
limit the range of output numbers, characters of stringsand length of arrays.

"""


import random
import string

## --------------- default values ----------------
DEFAULT = {
	'num_min': -1000,
	'num_max': 1000,
	'str_len_min': 1,
	'str_len_max': 10,
	'array_len_min': 1,
	'array_len_max': 10,
	'chars': string.ascii_uppercase + string.ascii_lowercase + string.digits + "_"
}

class Values(object):
	"""Generate random values

	Attributes:

		rand (Random): a Random instance used for generating all values
		num_min (int): Lower boundary of all output number (integer and float).
				All number generated will be greater than or equal to num_min, including those in array.
				The default value is -1000.
		num_max (int): Upper boundary of the output number (integer and float), including those in array.
				All values generated will be less than or equal to num_max.
				The default value is 1000.
		str_len_min (int): minimum length of all generated string, including those in array. Default: 1
		str_len_max (int): maximum length of all generated string, including those in array. Default: 10
		array_len_min (int): the minimum length of all array. Default: 1
		array_len_min (int): the maximum length of all array. Default: 10
		chars (str): all candidate characters in generating random string.
	"""
	def __init__(self, seed=None, **kwargs):
		"""Able to set seed and change parameters in initialization"""
		self.rand = random.Random()
		self.seed(seed)
		self.set_parameters(**kwargs)

	def set_parameters(self, **kwargs):
		"""change all internal parameters"""
		self.num_min = int(kwargs.get('num_min', DEFAULT['num_min']))
		self.num_max = int(kwargs.get('num_max', DEFAULT['num_max']))
		if self.num_max < self.num_min:
			raise ValueError('[num_max] must be equal or greater than [num_min]')

		self.str_len_min = int(kwargs.get('str_len_min', DEFAULT['str_len_min']))
		self.str_len_max = int(kwargs.get('str_len_max', DEFAULT['str_len_max']))
		if self.str_len_max < self.str_len_min:
			raise ValueError('[str_len_max] must be equal or greater than [str_len_min]')

		self.array_len_min = int(kwargs.get('array_len_min', DEFAULT['array_len_min']))
		self.array_len_max = int(kwargs.get('array_len_max', DEFAULT['array_len_max']))
		if self.array_len_max < self.array_len_min:
			raise ValueError('[array_len_max] must be equal or greater than [array_len_min]')

		self.chars = kwargs.get('chars', DEFAULT['chars'])

	def seed(self, seed=None):
		"""Initialize internal seed of Random instance"""
		self.rand.seed(seed)

	def randInt(self):
		return self.rand.randint(self.num_min, self.num_max)

	def randStr(self):
		str_len = self.rand.randint(self.str_len_min, self.str_len_max)
		return ''.join(self.rand.choice(self.chars) for _ in xrange(str_len))

	def randBool(self):
		return bool(self.rand.getrandbits(1))

	def randFloat(self):
		return self.rand.uniform(self.num_min, self.num_max)

	def randNum(self):
		"""generate a random number: a integer or a float point"""
		return self.randInt() if self.randBool() else self.randFloat()

	def randRangeDict(self):
		[small, large] = sorted([self.randInt(), self.randInt()])
		return {"$gte": small, "$lt": large}

	def randIntArray(self):
		"""Generate a array of random integer with random length"""
		array_len = self.rand.randint(self.array_len_min, self.array_len_max)
		return [self.randInt() for _ in xrange(array_len)]

	def randNumArray(self):
		"""Generate a array of random number with random length"""
		array_len = self.rand.randint(self.array_len_min, self.array_len_max)
		return [self.randNum() for _ in xrange(array_len)]

	def randStrArray(self):
		"""Generate a array of random string with random length"""
		array_len = self.rand.randint(self.array_len_min, self.array_len_max)
		return [self.randStr() for _ in xrange(array_len)]

	def randBoolArray(self):
		"""Generate a array of random boolean with random length"""
		array_len = self.rand.randint(self.array_len_min, self.array_len_max)
		return [self.randBool() for _ in xrange(array_len)]

# Create one instance, seeded from current time, and export its methods
# as module-level functions. The functions share state across all uses.

_inst = Values()
seed  = _inst.seed
set_parameters = _inst.set_parameters
randInt   = _inst.randInt
randStr   = _inst.randStr
randBool  = _inst.randBool
randFloat = _inst.randFloat
randNum   = _inst.randNum
randRangeDict = _inst.randRangeDict
randIntArray  = _inst.randIntArray
randNumArray  = _inst.randNumArray
randStrArray  = _inst.randStrArray
randBoolArray = _inst.randBoolArray
