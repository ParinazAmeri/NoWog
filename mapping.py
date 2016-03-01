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

import random
import string
from bson.son import SON
import values
import logging

"""
This module is used for mapping parse result into MongoDB command.

The core methods of mapping only include unpack(), makeSON() and mapping().

DBCommand class is specifically used for generate a instance of SON, which can be
directly used in db.command().

"""

def unpack(data, parent=[]):
	"""unpack parse result in order to unpack nested attributes.

	Can be used in generating query for find(), delete() and update()

	Examples:
		['A1', [['B1', 'num_match']]] -> ['A1.B1', 'num_match']
		['A1', [['B1', [['C1', 'arr_read_op', 'Text']]]]] -> ['A1.B1.C1', 'arr_read_op', 'Text']
	"""
	res = []
	for l in data:
		new_parent = parent+[l[0]]
		if isinstance(l[1], list):
			map(res.append, unpack(l[1], new_parent))
		else:
			res.append(['.'.join(new_parent)]+l[1:])
	return res



def makeSON(lst):
	"""Convert parsing result list (packed or unpacked) into a instance of SON.

	The first element (attribute) is KEY, and use '.' to combine all following
	element and use it as VALUE in SON.

	Example:
		['A1', [['B1', 'num_match']]] -> {'A1': {'B1': 'num_match'}}
		['A1.B1.C1', 'arr_read_op', 'Text'] -> {'A1.B1.C1': 'arr_read_op.Text'}
	"""
	res = SON()
	for l in lst:
		if isinstance(l[1], list):
			res[l[0]] = makeSON(l[1])
		else:
			res[l[0]] = '.'.join(l[1:])
	return res

def mapping(data, dictionary):
	"""Mapping a dictionary (SON) into a a MongoDB command.

	The idea is: all values are keywords of a lambda functions dictionary,
	each function take attribute as the only argument. Each lambda function
	will generate a SON file consist of proper form of MongoDB operation
	and a random values in designated place.

	Note:
		please notice that same keyword might represent different lambda
		function in different type of operation.
		E.g. Array.Num in update and insert represent different operator.

	Example:
		{'A1.B1': 'num_match'} + {'num_match' : lambda attr: {attr: self.values.randInt()},}
		--> return {'A1.B1': 130416}
	"""
	res = SON()
	for attr,cmd in data.items():
		if isinstance(cmd, dict): # nested document: {'A1': {'B1': 'num_match'}}
			res[attr] = mapping(cmd, dictionary)
		else:
			new = dictionary[cmd](attr)
			assert(len(new) == 1)
			k, v = new.items()[0]
			if k in res: # duplicate attribute -> operators in update, e.g. $set, $push
				res[k].update(v)
			else:
				res.update(new)
	return res


class DBCommand(object):
	"""Generate a instance of SON can be directly used by db.command()"""
	def __init__(self, seed=None, **kwargs):
		self.logger = logging.getLogger('DBCommand')
		self.logger.setLevel(logging.INFO)
		self.init_values(seed, **kwargs)
		self.query_dict = { # used for find() and delete()
			'True'  : lambda attr: {attr: True},
			'False' : lambda attr: {attr: False},
			'geo_op': lambda attr: {attr: {'$near': {'$geometry': {'type': 'Point', 'coordinates': [0, 0]},'$maxDistance': 50}}},
			'num_match' : lambda attr: {attr: self.values.randInt()},
			'text_read' : lambda attr: {attr: self.values.randStr()},
			'range_op'  : lambda attr: {attr: self.values.randRangeDict()},
			'arr_read_op' : lambda attr: {attr: self.values.randIntArray()},
			'arr_read_op.Text' : lambda attr: {attr: self.values.randStrArray()},
			'arr_read_op.Num'  : lambda attr: {attr: self.values.randIntArray()},
			'arr_read_op.Bool' : lambda attr: {attr: self.values.randBoolArray()},
			'arr_read_op.range_op' : lambda attr: {attr: {'$elemMatch': self.values.randRangeDict()}},
		}
		self.sort_dict = { # used for find()
			'1' : 1,
			'-1': -1
		}
		self.update_dict = { # used for update()
			'True' : lambda attr: {'$set': {attr: True}},
			'False': lambda attr: {'$set': {attr: False}},
			'num_match'  : lambda attr: {'$set': {attr: self.values.randInt()}},
			'text_write' : lambda attr: {'$set': {attr: self.values.randStr()}},
			'Array.Text' : lambda attr: {'$set': {attr: self.values.randStrArray()}},
			'Array.Num'  : lambda attr: {'$set': {attr: self.values.randIntArray()}},
			'Array.Bool' : lambda attr: {'$set': {attr: self.values.randBoolArray()}},

			'arr_add_op.Text' : lambda attr: {'$push': {attr: self.values.randStr()}},
			'arr_add_op.Num'  : lambda attr: {'$push': {attr: self.values.randInt()}},
			'arr_add_op.Bool' : lambda attr: {'$push': {attr: self.values.randBool()}},

			'arr_remove_op.Text' : lambda attr: {'$push': {attr: self.values.randStrArray()}},
			'arr_remove_op.Num'  : lambda attr: {'$push': {attr: self.values.randIntArray()}},
			'arr_remove_op.Bool' : lambda attr: {'$push': {attr: self.values.randBoolArray()}},
		}
		self.document_dict = { # used for inert()
			'True'  : lambda attr: {attr: True},
			'False' : lambda attr: {attr: False},
			'num_match'  : lambda attr: {attr: self.values.randInt()},
			'text_write' : lambda attr: {attr: self.values.randStr()},
			'Array.Text' : lambda attr: {attr: self.values.randStrArray()},
			'Array.Num'  : lambda attr: {attr: self.values.randIntArray()},
			'Array.Bool' : lambda attr: {attr: self.values.randBoolArray()},
		}

	def init_values(self, seed=None, **kwargs):
		self.values = values.Values(seed, **kwargs)

	def makeCommands(self, read, write, sort, size=1, coll_name='undefined'):
		if self.isFind(read, write):
			return self.makeFindCmds(read, sort, size, coll_name)
		elif self.isInsert(read, write):
			return self.makeInsertCmds(write, size, coll_name)
		elif self.isUpdate(read, write):
			return self.makeUpdateCmds(read, write, size, coll_name)
		elif self.isDelete(read, write):
			return self.makeDeleteCmds(read, size, coll_name)
		else:
			self.hanlde_err_type(read, write)



	# -------------------------------------------------------------------
	# 				|	read == []	|	read != []	|	read==['ALL']	|
	# -------------------------------------------------------------------
	# write == []	|		x		|	  find 		|		 x   		|
	# -------------------------------------------------------------------
	# write != []	|	  insert	|	  update	|	 update all		|
	# -------------------------------------------------------------------
	# write==[NULL]	|		x		|	  delete	|		 x 			|
	# -------------------------------------------------------------------
	def isFind(self, read, write):
		return read != [] and read[0] != 'ALL' and write == []
	def isUpdate(self, read, write):
		return read != [] and write != [] and write[0] != 'NULL'
	def isInsert(self, read, write):
		return read == [] and write != [] and write[0] != 'NULL'
	def isDelete(self, read, write):
		return read != [] and read[0] != 'ALL' and write[0] == 'NULL'
	def hanlde_err_type(self, read, write):
		err_str = 'Operation type error: '
		if read == [] and write == []:
			raise TypeError(err_str + 'at least either <read> or <write> should have one input phrase')
		elif read == [] and write[0] == 'NULL':
			raise TypeError(err_str + 'for operation [delete], <read> should have at least one input phrase')
		elif read[0] == 'ALL' and write == []:
			raise TypeError(err_str + 'for operation [update], <write> should have at least one input phrase')
		elif read[0] == 'ALL' and write[0] == 'NULL':
			raise TypeError(err_str + 'Keyword "ALL" and "NULL" cannot be used together')




	def makeFindCmds(self, read, sort, size=1, coll_name='undefined'):
		self.logger.info('making %d commands: [find]' % size)
		queries = self.makeQuery(read, size)
		sort = self.makeSort(sort)
		return [self.getFindTemplate(q, sort, coll_name) for q in queries]
	def makeUpdateCmds(self, read, write, size=1, coll_name='undefined'):
		self.logger.info('making %d commands: [update]' % size)
		queries = self.makeQuery(read, size)
		updates = self.makeUpdate(write, size)
		return [self.getUpdateTemplate(queries[i], updates[i], coll_name) for i in xrange(size)]
	def makeInsertCmds(self, write, size=1, coll_name='undefined'):
		self.logger.info('making %d commands: [insert]' % size)
		documents = self.makeDocuments(write, size)
		return [self.getInsertTemplate(d, coll_name) for d in documents]
	def makeDeleteCmds(self, read, size=1, coll_name='undefined'):
		self.logger.info('making %d commands: [delete]' % size)
		queries = self.makeQuery(read, size)
		return [self.getDeleteTemplate(q, coll_name) for q in queries]

	def makeQuery(self, read, size=1):
		if read[0] == 'ALL': return [SON()]*size
		read_unpacked = unpack(read)
		read_SON = makeSON(read_unpacked)
		return [mapping(read_SON, self.query_dict) for _ in xrange(size)]
	def makeUpdate(self, write, size=1):
		write_unpacked = unpack(write)
		write_SON = makeSON(write_unpacked)
		return [mapping(write_SON, self.update_dict) for _ in xrange(size)]
	def makeDocuments(self,write, size=1):
		# NO unpack!!
		write_SON = makeSON(write)
		return [mapping(write_SON, self.document_dict) for _ in xrange(size)]
	def makeSort(self, sort):
		if sort == [] or sort[0] == 'NULL': return None
		else: return SON([ (lst[0], self.sort_dict[lst[1]]) for lst in sort ])

	# https://docs.mongodb.org/manual/reference/command/find/#dbcmd.find
	# {
	# 	"find": <string>,
	# 	"filter": <document>,
	# 	"sort": <document>,
	# }
	def getFindTemplate(self, query, sort, coll_name='undefined'):
		find = SON([
				('find', coll_name),
				('filter', query)])
		if sort: find['sort'] = sort
		return find
	# https://docs.mongodb.org/manual/reference/command/update/#dbcmd.update
	# {
	# 	update: <collection>,
	# 	updates:
	# 		[
	# 			{ q: <query>, u: <update>, upsert: <boolean>, multi: <boolean> },
	# 			...
	# 		],
	# }
	def getUpdateTemplate(self, query, update, coll_name):
		return SON([
				('update', coll_name),
				('updates',[
						SON([('q', query), ('u', update), ('multi', True)])
					])
			])
	# https://docs.mongodb.org/manual/reference/command/insert/#dbcmd.insert
	# {
	# 	insert: <collection>,
	# 	documents: [ <document>, <document>, <document>, ... ],
	# }
	def getInsertTemplate(self, document, coll_name):
		return SON([
				('insert', coll_name),
				('documents', [document])
			])
	# https://docs.mongodb.org/manual/reference/command/delete/#dbcmd.delete
	# {
	# 	delete: <collection>,
	# 	deletes: [
	# 		{ q : <query>, limit : <integer> },
	# 		...
	# 	],
	# }
	def getDeleteTemplate(self, query, coll_name):
		return SON([
				('delete', coll_name),
				('deletes', [SON([('q', query),('limit', 0)])])
			])




# if __name__ == '__main__':
# 	read = [['A1', 'False'], ['A2', 'num_match'], ['A3', [['B1', 'text_read']]]]
# 	# print make_Queries(read,3)
# 	db_cmd = DBCommand()
# 	finds = db_cmd.makeFindCmds(read, ['NULL'], 2)
# 	import json
# 	for f in finds:
# 		print json.dumps(f, indent=4)
