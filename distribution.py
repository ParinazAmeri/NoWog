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


import numpy as np

class Distribution(object):
	"""Draw samples under specific type of distribution

	Note:
		The sample under "uniform" distribution is actually generated
		by numpy.linspace, in order to provide a more evenly distributed
		samples

	"""

	def __init__(self, seed=None):
		self.seed(seed)

	def seed(self, seed=None):
		"""Change the seed in numpy.random"""
		np.random.seed(seed)

	def drawSamples(self, d_type, low, high, size, *args):
		"""Draw samples based on distribution type (d_type)

		Note:
			It should be the only interface that this generator should use

		Args:
			d_type (str): distribution type: {uniform, normal}
			low (float/int): Lower boundary of the output samples.
							 All values generated will be greater than or equal to low
			high (float/int): Upper boundary of the output samples.
								All values generated will be less than high.
			size: (int): total amount of output samples
			*args: [float]: additional arguments required by different distribution
		"""
		if d_type == 'uniform':
			return self.linspace(low, high, size)
			# return self.uniform(low, high, size)
		# elif d_type == 'linspace':
		# 	return self.linspace(low, high, size)
		elif d_type == 'normal':
			return self.normal(low, high, size, args[0])
		else:
			raise KeyError('Unknown distribution type: [%s]. Available types include: {uniform, normal}' % d_type)

	def uniform(self, low, high, size):
		return sorted(np.random.uniform(low, high, size))

	def linspace(self, low, high, size):
		return np.linspace(low, high, size, endpoint=False)

	def normal(self, low, high, size, sigma):
		"""Draw sample from normal distribution
		Note:
			mu will be generated automatically. Only sigma is required.
		"""
		mu = (low + high) / 2.0
		res = []
		while len(res) < size:
			temp = np.random.normal(mu, sigma, size)
			temp = filter(lambda x: low <= x < high, temp)
			res.extend(temp)
		return sorted(res[:size])

	def exponential(self):
		pass

	def linear(self):
		pass

	def polynomial(self):
		pass


_inst = Distribution()
drawSamples = _inst.drawSamples
seed = _inst.seed

