#!/usr/bin/env python

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
#    along with Nowog.  If not, see <http://www.gnu.org/licenses/>.

"""NoWog (Not only Workload Generator)

NoWog is a workload generator able to generate and execute customizable MongoDB
workload based on a specific input format defined in doc/EBNF_gammar.txt

NoWog consist of three parts:

	- Parser: use pyparsing to parse the BNF input.
			Parser result consist of ID of each rule, distribution and operation information.

	- Mapping: map the parser result into MongoDB command.
				This part use distribution.py to draw sampled from specified distribution.
				And use values.py to generate all random values in each command.
				Each rule will be mapped as a session, which consist of its ID and a
				execution time table.

	- Execution: execute all sessions.
				This part are also able to display histogram of specific type or IDs of workload.


Usage example:
	If run without any arguments, program will exit after generate (or write)
	sessions file.

		$ python main.py

	Display workload histogram for all operations of all sessions.

		$ python main.py --show

	Only run one operation in each session once, in order to test the correctness
	and runnability of the generated command.

		$ python main.py --try

	Run all operations in all sessions under prearranged distribution.

		$ python main.py --run


Note:
	NoWog required MongoDB Version 3.2

"""

__author__ 		= "Haipeng Guan, Parinaz Ameri"
__copyright__ 	= "Copyright 2016 Parinz Ameri, Haipeng Guan"
__credits__ 	= ["Haipeng Guan", "Parinaz Ameri", "Nico Schlitter", "Joerg Meyer"]
__license__ 	= "GPL-3"
__version__ 	= "1.0.1"
__date__ 		= "29.02.2016"
__maintainer__ 	= "Haipeng Guan, Parinaz Ameri"
__email__ 		= "guanhaipeng@gmail.com, parinaz.ameri@kit.edu"
__status__ 		= "beta"

from bson.son import SON
import ConfigParser
import argparse
import logging
import json

import distribution
import mapping
import parser
import executor

# global logger
logger = logging.getLogger('NoWog')

# configuration file name
CONFIG_FILE = 'config.ini'


def init_logger():
	ch = logging.StreamHandler()
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	ch.setFormatter(formatter)
	ch.setLevel(logging.INFO)

	exec_logger = logging.getLogger('executor')
	exec_logger.setLevel(logging.INFO)
	exec_logger.addHandler(ch)

	db_cmd_logger = logging.getLogger('DBCommand')
	db_cmd_logger.setLevel(logging.INFO)
	db_cmd_logger.addHandler(ch)

	logger = logging.getLogger('NoWog')
	logger.setLevel(logging.INFO)
	logger.addHandler(ch)
	return logger

def init_config(config_file):
	logger.info('Reading configuration file [%s]' % config_file)
	DEFAULT_CONFIG = {
		'input_files': [],
		'save_parser': '',
		'save_sessions': '',
		'db_name': 'NoWog',
		'coll_name': 'NoWog_test',
		'URL': 'mongodb://localhost',
		'seed': None,
	}
	config = ConfigParser.SafeConfigParser(DEFAULT_CONFIG)
	if not config.read(config_file):
		logger.error('Unable to read configuration file: [%s]' % config_file)
		logger.error('Program exit with error')
		exit()
	return config



def makeTimeTable(d_info, parser_result, db_cmd):
	"""Generate execution time table.
	Use distribution information to generate time stamps.
	Use parse result to generate MongoDB operations, a.k.a parameter for runCommand()
	"""
	read, write, sort = parser_result.values()
	samples = distribution.drawSamples(d_info['type'],
										d_info['time_period'][0], d_info['time_period'][1],
										d_info['total'], *d_info['parameters'])
	try:
		cmds = db_cmd.makeCommands(read, write, sort, len(samples), coll_name)
	except TypeError, e:
		logger.error('failed to mapping into MongoDB command: %s' % str(e))
		logger.error('program exit with error')
		exit()
	res = {}
	for i in xrange(len(samples)):
		res[samples[i]] = cmds[i]
	# res = {samples[i]: cmds[i] for i in xrange(len(samples))}
	assert(len(res) == d_info['total'])
	return res


def connectDB(MongoDB_URL):
	from pymongo import MongoClient
	try:
		client = MongoClient(MongoDB_URL)
	except Exception, e:
		logger.error('Unable to connect to database: %s' % str(e))
		logger.error('program exit with error')
		exit()
		# raise e
	logger.info('connection established')
	return client





if __name__ == '__main__':
	# # ---------------------------------------
	# # # # # #  initialize argparse  # # # # #
	# # ---------------------------------------
	arg_parser = argparse.ArgumentParser(description='Given no arguments, the program will stop after saving session file')
	arg_parser.add_argument('-t','--try', dest='try_run',help='execute each command once. In order to make sure all commands are runnable', action='store_true')
	arg_parser.add_argument('-r','--run',help='run all commands under schedule', action='store_true')
	arg_parser.add_argument('--show',dest='showType',help='Display workload schedule diagram of specific operation type. Default is "all" operation', choices=['all', 'find', 'insert', 'update', 'delete'], nargs='?', const='all')
	arg_parser.add_argument('--showid',help='Display workload schedule diagram of specific ID',nargs='+')
	args = arg_parser.parse_args()
	logger = init_logger()
	if not (args.try_run or args.run or args.showType or args.showid):
		logger.warning('Given no arguments, the program will stop after saving session file')

	# # ---------------------------------------------
	# # # # # #  handle configuration file  # # # # #
	# # ---------------------------------------------
	config = init_config(CONFIG_FILE)

	BNF_infiles = filter(None, [x.strip() for x in config.get('inputs', 'input_files').split(',')])
	save_parser = config.get('outputs', 'save_parser')
	save_sessions = config.get('outputs', 'save_sessions')
	db_name   = config.get('connection', 'db_name')
	coll_name = config.get('connection', 'coll_name')
	seed = config.getint('seed', 'seed')
	MongoDB_URL = config.get('connection', 'URL')
	values_kwargs = {}
	exec_kwargs = {}
	if 'additional_value_setting' in config._sections:
		values_kwargs = config._sections['additional_value_setting']
	if 'additional_execution_setting' in config._sections:
		def str_to_bool(strr):
			if strr.lower() == 'true':  return True
			if strr.lower() == 'false': return False
			return strr
		exec_kwargs = config._sections['additional_execution_setting']
		for k,v in exec_kwargs.items():
			exec_kwargs[k] = str_to_bool(v)
		# exec_kwargs = {k: str_to_bool(v) for k,v in exec_kwargs.items()}



	# # ---------------------------------------------
	# # # # # read BNF, parsing and mapping # # # # #
	# # ---------------------------------------------
	sessions = {}

	if BNF_infiles != []:
		for bnf_file in BNF_infiles:
			logger.info('Parse BNF files [%s]' % bnf_file)
			with open(bnf_file, 'r') as f:
				rulesetStr = f.read()
			sessions.update(parser.parse_rulesetStr(rulesetStr))

		# saving parser result
		if save_parser:
			logger.info('Saving parsing result in [%s]' % save_parser)
			with open(save_parser, 'w') as f:
				json.dump(sessions, f, indent=4)
		else:
			logger.warning('No parser result will be saved')

		# Mapping BNF into parameters of runCommand
		logger.info('=== Mapping stage ===')
		logger.info('initializing distribution seed: [%r]' % seed)
		distribution.seed(seed)
		try:
			logger.info('initializing mapping module')
			db_cmd = mapping.DBCommand(seed, **values_kwargs)
		except ValueError, e:
			logger.error('initialize mapping module failed: %s' % str(e))
			logger.error('Program exit with error')
			exit()
		for ID in sessions:
			logger.info('mapping session [%s]' % ID)
			sessions[ID] = makeTimeTable(sessions[ID]['distribution'], sessions[ID]['parser_result'], db_cmd)
	else:
		logger.error('No input files')
		logger.error('Program exit with error')
		exit()

	# # ---------------------------------------------
	# # # # # # # saving session files # # # # # # #
	# # ---------------------------------------------
	save_sessions = config.get('outputs', 'save_sessions')
	if save_sessions:
		logger.info('saving sessions in [%s]' % save_sessions)
		with open(save_sessions, 'w') as f:
			json.dump(sessions, f, indent=4)
	else:
		logger.warning('No sessions files will be saved')


	# # ---------------------------------------------
	# # # # # # # # # execution! # # # # # # # # #
	# # ---------------------------------------------
	if args.showType or args.showid or args.try_run or args.run:
		logger.info('initializing executor')
		exe = executor.Executor(**exec_kwargs)

		for ID in sessions:
			logger.info('Add session [%s] into executor' % ID)
			exe.addSession(ID, sessions[ID])

		if args.showType or args.showid:
			logger.info('Displaying histogram')
			exe.show(args.showType, args.showid)

		if args.try_run or args.run:
			logger.info('Connecting to database')
			db = connectDB(MongoDB_URL)[db_name]
			exe.setCollection(db[coll_name])

			if args.try_run:
				exe.try_run()
			if args.run:
				exe.run()
		logger.info('all executions finish')
	else:
		logger.info('No further execution arguments specified')
		logger.info('program exit')



