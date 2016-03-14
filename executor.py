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

import sched, time
import logging

class Executor(object):
	"""MongoDB operation executor

	This executor use session as a unit to import operation and time table.
	Each session consist of an ID, a list of operation and their corresponding
	execution time.

	It use sched.scheduler to arrange the execution.
	It can also display histogram of number of operation across a time interval.

	Attributes:

		logger (Logger): internal logger.
		sche (sched.scheduler): scheduler for all MongoDB operations
		sessions_queue {str: {float: SON}}: Queue for all sessions added into executor
											It's structure is {ID: {delay: cmd,....}}.
		db (pymongo.database.Database): MongoDB database instance.
		collection (pymongo.collection.Collection): The collection in which all workload will be executed
		type_cache (dict): cache all operation types when adding into executor. Used for displaying.
		reset_prof (bool): If True, disable, drop and enable system.profile before try_run() and run(). Default is False
		profile_size (int): The size (MB) of re-create system.profile collection. Valid only when reset_prof is true. Default is 1 MB
		drop_coll (bool): If True, drop designed collection before try_run() and run(). Default is False.
		creat_coll (bool): If True, create designed collection if not exist before try_run() and run(). Default is True.
		DB_initialized (bool): True when collection is set.
		bins (int): bins used in matplotlib.pyplot.hist()


	Args:
		collection (pymongo.collection.Collection): The collection in which all workload will be executed
		**kwargs: Initialize some attributes including: reset_profiling, profile_size, drop_collection, create_collection and bins

	"""
	def __init__(self, collection=None, **kwargs):
		self.logger = logging.getLogger('executor')
		self.logger.setLevel(logging.INFO)
		self.sche = sched.scheduler(time.time, time.sleep)
		self.sessions_queue = {} # {ID: {delay: cmd, delay2: cmd2, ....}}
		self.setCollection(collection)
		self.reset_prof = kwargs.get('reset_profiling', False)
		self.profile_size = int(kwargs.get('profile_size', 1)) # 1 MB by default
		self.drop_coll = kwargs.get('drop_collection', False)
		self.creat_coll = kwargs.get('create_collection', True)
		self.bins = int(kwargs.get('bins', 20))
		self.time_scale_factor = float(kwargs.get('time_scale_factor', 1.0))
		self.histtype = kwargs.get('histtype', 'step')
		self.type_cache = { # caching for display
			'find' : [], # [ID(str), ...]
			'insert' : [],
			'update' : [],
			'delete' : []
		}

	def setCollection(self, collection=None):
		if collection:
			self.db = collection.database
			self.collection = collection
			self.DB_initialized = True
		else:
			self.DB_initialized = False

	def addSession(self, ID, time_table, priority=1):
		"""Add a session into executor.

		Args:
			ID (str): session ID
			time_table::
				{
					time(float): cmd(SON),
					time(float): cmd(SON),
					time(float): cmd(SON),
					.....
				}
			priority (int): the priority of execution of this session

		Note:
			"time" in time_table represent the delay of execution after executor begin.
			When duration of certain operation is too long, whole execution will delay.
			Read more about scheduler in: https://docs.python.org/2/library/sched.html

		"""
		if ID in self.sessions_queue:
			# raise KeyError('ID [%s] already exist!' % ID)
			logger.warning('ID [%s] already exist in executor\'s session queue!' % ID)
			logger.warning('New operation will overwrite old one')
		time_table = {t*self.time_scale_factor: time_table[t] for t in time_table}
		self.sessions_queue[ID] = time_table
		cmd_type = time_table.values()[0].keys()[0]
		if cmd_type in self.type_cache:
			self.type_cache[cmd_type].append(ID)
		for t in time_table:
			self.sche.enter(t+3, priority, self.runCommand, [ID, time_table[t]])

	def runCommand(self, ID, cmd):
		self.logger.info('Running: [%s]' % ID)
		return self.db.command(cmd)


	def init_execution(self):
		"""Initial stage before run() and try_run()

		Checking whether database initialized; drop collection, create collection
		and reset profiling in MongoDB collection if need.
		"""
		if not self.DB_initialized:
			raise RuntimeError('Database uninitialized!')
		if self.drop_coll:
			self.logger.info('Drop collection: [%s]' % self.collection.name)
			self.collection.drop()
		if self.creat_coll:
			if self.collection.name in self.db.collection_names():
				self.logger.info('Collection [%s] already exist' % self.collection.name)
			else:
				self.logger.info('Create collection: [%s] in database [%s]' % (self.collection.name, self.db.name))
				self.db.create_collection(self.collection.name)
		if self.reset_prof:
			self.logger.info('Reset profiling')
			self.db.set_profiling_level(0)
			self.db.system.profile.drop()
			self.logger.info('Creating system.profile with [%d] MB' % self.profile_size)
			self.db.create_collection( "system.profile", capped=True, size=1024*1024*self.profile_size)
			self.db.set_profiling_level(2)

	def run(self):
		self.init_execution()
		self.logger.info('# # # # # # # # Start execution # # # # # # # # #')
		self.sche.run()
		self.logger.info('# # # # # # # # Execution finish # # # # # # # # #')


	def try_run(self):
		self.init_execution()
		self.logger.info('# # # # # # # # Trying to execute # # # # # # # # #')
		for ID in self.sessions_queue:
			self.runCommand(ID, self.sessions_queue[ID].values()[0])
		self.logger.info('# # # # # # # # Try_run finish # # # # # # # # #')


	def show(self, showType, showID):
		"""Display histogram of operation
		Args:
			showType (str): Type of displaying operation: {all, find, update, insert, delete}.
			showID [str]: A list of ID which specifically want to display.

		Note:
			showType and showID can be used at the same time. If there is no designated type
			of operation in the list of showID, then nothing will display.
		"""
		if not showType and not showID: return
		if showID and not showType: showType = 'all'

		import matplotlib.pyplot as plt
		if showType == 'all':
			title = 'Total Workload of all operations'
			target_ID = self.sessions_queue.keys()
		elif showType in self.type_cache:
			title = 'Workload of [%s] operations' % showType
			target_ID = self.type_cache[showType]
		else:
			# raise KeyError('Unknown command type: %s' % showType)
			self.logger.error('Unknown command type: %s' % showType)
			return

		if showID:
			target_ID = filter(lambda x: x in showID, target_ID)
			if len(target_ID) < len(showID):
				not_found = filter(lambda x: not x in target_ID, showID)
				self.logger.warning('Unable to found these ID: %r in [%s] operation' % (not_found, showType) )
			title += 'in %s' % target_ID

		if len(target_ID) == 0:
			# raise RuntimeError('No [%s] operation found. Stop displaying' % (showType))
			self.logger.error('No [%s] operation found. Stop displaying' % (showType))
			return
		all_samples = [self.sessions_queue[ID].keys() for ID in target_ID]
		plt.hist(all_samples, self.bins*len(target_ID), label=target_ID, histtype=self.histtype)
		plt.xlabel('time (sec)')
		plt.ylabel('number of query')
		plt.title(title)
		plt.legend()
		plt.show()

