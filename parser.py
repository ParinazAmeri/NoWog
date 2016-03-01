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

from pyparsing import *
import json
import argparse

LSQUARE, RSQUARE, SEMI, COLON, ASSIGN, COMMA, DOT = map(Suppress, '[];:=,.')
LBRACE, RBRACE, LBRACK, RBRACK, MINUS = map(Suppress, '{}()-')

attribute = Word(alphanums+'_'+'.')
floatNumber = Regex(r'[-+]?\d+(\.\d*)?([eE]\d+)?')
sort_opt = ( Literal('1') | Literal('-1'))('sort_opt')
minute = Word(nums)('minute')
session_ID = Word(alphas, alphanums+'_')

distribution = (CaselessLiteral('uniform') | CaselessLiteral('normal') | CaselessLiteral('exponential')
				| CaselessLiteral('linear') | CaselessLiteral('polynomial'))
total 	  = Word(nums)
arguments = ZeroOrMore(floatNumber + COMMA) + total
absolute  = distribution + LBRACK + Group(arguments)('arguments') + RBRACK

arr_read_type 	 = Keyword('Bool') | Keyword('Num') | Keyword('Text') | Keyword('range_op')
arr_write_type 	 = Keyword('Bool') | Keyword('Num') | Keyword('Text')
array_read = Keyword('arr_read_op') + Optional(DOT + arr_read_type)
array_write = (Keyword('arr_add_op') | Keyword('arr_remove_op') | Keyword('Array')) + DOT + arr_write_type

num_match 	 = Keyword('num_match')
geo_op 		 = Keyword('geo_op')
range_op 	 = Keyword('range_op')
number_read  = num_match | geo_op | range_op
number_write = num_match


text_read  = Keyword('text_read')
text_write = Keyword('text_write')
bool_op = ( Keyword('True') | Keyword('False') )

document_read  = Forward()
document_write = Forward()
read_type    = Forward()
write_type   = Forward()
read_phrase  = Forward()
write_phrase = Forward()

document_read  << OneOrMore(Group(read_phrase))
document_write << OneOrMore(Group(write_phrase))

read_type  << (bool_op | text_read  | number_read  | array_read  | Group(document_read) )
write_type << (bool_op | text_write | number_write | array_write | Group(document_write))

read_phrase  << ( LBRACK + attribute + COLON + (read_type )('read_type') + RBRACK )
write_phrase << ( LBRACK + attribute + COLON + (write_type)('write_type')+ RBRACK )

read  = ( LBRACE + (ZeroOrMore(Group(read_phrase ))('read_phrase' )) + RBRACE ) | Keyword('ALL')
write = ( LBRACE + (ZeroOrMore(Group(write_phrase))('write_phrase')) + RBRACE ) | Keyword('NULL')
sort  = (LBRACE + ZeroOrMore(LBRACK + Group(attribute + COLON + sort_opt)+ RBRACK) + RBRACE) | Keyword('NULL')
time_period = minute + MINUS + minute

quadruple = ( Group(read)('read') + COMMA + Group( write )('write') + COMMA + Group(sort)('sort') + COMMA + Group(time_period)('time_period') )
rule 	  = session_ID + COLON + LBRACE + quadruple('quadruple') + ASSIGN + Group(absolute)('absolute') + RBRACE + SEMI
ruleset   = (LBRACE + OneOrMore(Group(rule)) + RBRACE).ignore('#' + restOfLine)

def parse_rulesetStr(rulesetStr):
	ruleList = ruleset.parseString(rulesetStr).asList()
	ruleset_dict = {}
	for rule in ruleList:
		[ID, read, write, sort, time_interval, absolute] = rule
		time_interval = sorted([float(i) for i in time_interval])
		disType = absolute[0].lower()
		paras = [float(i) for i in absolute[1][:-1]]
		total = int(absolute[1][-1])
		ruleset_dict.update({
			ID: {
				'distribution': {
					'type': disType,
					'time_period': time_interval,
					'total': total,
					'parameters': paras,
				},
				'parser_result':{
					'read' : read,
					'write': write,
					'sort' : sort,
				}
			}
		})
	return ruleset_dict



if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--in', dest='infiles', nargs='+', help='input file names. More than one file available', required=True)
	parser.add_argument('--out', dest='outfiles', help='the output file name.', required=True)
	args = parser.parse_args()
	all_ruleset_dict = {}
	for files in args.infiles:
		with open(files, 'r') as f:
			rulesetStr = f.read()
		new_ruleset = parse_rulesetStr(rulesetStr)
		override = filter(lambda x: x in all_ruleset_dict.keys(), new_ruleset.keys())
		if override != []:
			raise Exception('ID collision error: %r in [%s]' % (override, files))
		all_ruleset_dict.update(new_ruleset)
	with open(args.outfiles, 'w') as f:
		json.dump(all_ruleset_dict,f, indent=4)
