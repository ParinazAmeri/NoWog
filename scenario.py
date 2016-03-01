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

"""Scenario generator.

This scenario generator is actually a BNF input file generator.

A scenario including loading stage and workload stage.

For loading stage:
	This generator will generate a single insert rule based on
	write phrase and collection size provided in scenario.ini.
	The result of this stage can be used for initialize dataset in collection.

For workload stage:
	This stage will generate maximum three rules (find, insert and update) based
	on the workload configuration in scenario.ini. The attributes in find() and
	insert() is randomly chosen from write phase provided in loading stage.

About the complexity of operation:
	simple operation: no nested attributes
	complicate operation: only nested attributes, e.g. {'A1.B1.C1': 130416}

"""


import json
from bson.son import SON
import numpy as np
import parser
import mapping
import random
import logging
import ConfigParser






TEMPELATE_RULE = """
	%s: {
		%s,
		%s,
		%s,
		%s - %s = uniform(%s)
	};"""


logger = logging.getLogger('scenario')


config = ConfigParser.SafeConfigParser()
config.read('scenario.ini')
load_BNF_outfile 	 = config.get('outputs', 'load_BNF')
workload_BNF_outfile = config.get('outputs', 'workload_BNF')
coll_size = config.getint('load_dataset', 'coll_size')
write_str = config.get('load_dataset', 'write')
is_simple_cmd = (config.get('workload', 'complexity') == 'simple')
start_time = config.getint('workload', 'start_time')
end_time   = config.getint('workload', 'end_time')
total_workload = config.getint('workload', 'total_workload')
workload_type = config.get('workload', 'type')

def getRatios(workload_type):
	index = {
		'read_only'   : [100, 0, 0], # [read, update, insert]
		'update_only' : [0, 100, 0],
		'insert_only' : [0, 0, 100],
		'read_mostly' : [95, 5, 0],
		'update_mostly':[50, 50, 0],
		'custom': [config.getint('ratio', 'read'), config.getint('ratio', 'update'), config.getint('ratio', 'insert')]
	}
	return index[workload_type]





def attrFilter(data_SON, simple=True):
	"""choose the simple/complicate attributes from parse result (as SON)."""
	if simple:
		logger.info('select all simple attributes')
	else:
		logger.info('select all complicate attributes')
	res = {
		'simple': SON(),
		'complicate': SON()
	}
	for attr in data_SON:
		if '.' in attr:
			res['complicate'][attr] = data_SON[attr]
		else:
			res['simple'][attr] = data_SON[attr]
	return res['simple'] if simple else res['complicate']



def makeRead(attributes):
	dictionary = {
		'True'  : 'True',
		'False' : 'False',
		'num_match'  : 'num_match',
		'text_write' : 'text_read',
		'Array.Text' : 'arr_read_op.Text',
		'Array.Num'  : 'arr_read_op.Num',
		'Array.Bool' : 'arr_read_op.Bool'
	}
	target_attr = random.sample(attributes, random.randint(1, len(attributes)))
	res = ''
	for k in target_attr:
		res += '(%s: %s)' % (k, dictionary[attributes[k]])
	return '{%s}' % res
def makeSort(attributes):
	target_attr = random.sample(attributes, random.randint(1, len(attributes)))
	def value():
		return 1 if bool(random.getrandbits(1)) else -1
	res = ''
	for k in target_attr:
		res += '(%s: %s)' % (k, value())
	return '{%s}' % res
def makeWrite(attributes):
	target_attr = random.sample(attributes, random.randint(1, len(attributes)))
	res = ''
	for k in target_attr:
		res += '(%s: %s)' % (k, attributes[k])
	return '{%s}' % res



def makeInsertRule(write, size, start=end_time, end=end_time):
	logger.info('making insert rule in total number %s from %ss to %ss' % (size, start, end))
	ID = 'INSERT_RULE'
	read = '{}'
	sort = 'NULL'
	return TEMPELATE_RULE % (ID, read, write, sort, start, end, size)
def makeFindRule(read, sort, size, start=start_time, end=end_time):
	logger.info('making find rule in total number %s from %ss to %ss' % (size, start, end))
	ID = 'FIND_RULE'
	write = '{}'
	return TEMPELATE_RULE % (ID, read, write, sort, start, end, size)
def makeUpdateRule(read, write, size, start=start_time, end=end_time):
	logger.info('making update rule in total number %s from %ss to %ss' % (size, start, end))
	ID = 'UPDATE_RULE'
	sort = 'NULL'
	return TEMPELATE_RULE % (ID, read, write, sort, start, end, size)



def initLogger():
	ch = logging.StreamHandler()
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	ch.setFormatter(formatter)
	ch.setLevel(logging.INFO)
	global logger
	logger.setLevel(logging.INFO)
	logger.addHandler(ch)
	return logger



if __name__ == '__main__':
	initLogger()
	load_ruleset = '{%s\n}' % makeInsertRule(write_str, coll_size, 0, 1)
	logger.info('saving load BNF file in [%s]' % load_BNF_outfile)
	with open(load_BNF_outfile, 'w') as f:
		f.write(load_ruleset)
	write_parsed = parser.parse_rulesetStr(load_ruleset).values()[0]['parser_result']['write']
	write_unpacked = mapping.unpack(write_parsed)
	write_SON = mapping.makeSON(write_unpacked)
	target_attr = attrFilter(write_SON, is_simple_cmd)

	ratios = getRatios(workload_type)
	if sum(ratios) != 100:
		raise ValueError('sum of all ratio should be 100')
	[read_size, update_size, insert_size] = [int(r/100.0*total_workload) for r in ratios]

	final_ruleset = ''

	# making find rule
	if read_size > 0:
		read_str  = makeRead(target_attr)
		sort_str  = makeSort(target_attr) if bool(random.getrandbits(1)) else 'NULL'
		find_rule = makeFindRule(read_str, sort_str, read_size)
		final_ruleset += find_rule

	# making update rule
	if update_size > 0:
		read_str  = makeRead(target_attr) if bool(random.getrandbits(1)) else 'ALL'
		write_str = makeWrite(target_attr)
		update_rule = makeUpdateRule(read_str, write_str, update_size)
		final_ruleset += update_rule

	# making insert rule
	if insert_size > 0:
		write_str = scenario_setting['write']
		insert_rule = makeInsertRule(write_str, insert_size)
		final_ruleset += update_rule

	final_ruleset = '{%s\n}' % final_ruleset

	logger.info('saving workload BNF file in [%s]' % workload_BNF_outfile)
	with open(workload_BNF_outfile, 'w') as f:
		f.write(final_ruleset)









