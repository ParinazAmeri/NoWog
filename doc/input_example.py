read_sample_with_comment = (
'{'
	'(A1 : True)'
	'(A1 : False)'
	'(A2 : text_read)'
	'(A3 : num_match)'
	'(A3 : geo_op)'
	'(A3 : range_op)'
	'(A4 : arr_read_op)'		# same as "arr_read_op.Num"
	'(A4 : arr_read_op.Bool)'	# NOT "arr_read_op;Bool", right?
	'(A4 : arr_read_op.Text)'
	'(A4 : arr_read_op.Num)'
	'(A4 : arr_read_op.range_op)'
	'(A5 : (B1 : True)(B2 : text_read))'
	'(A5 : (B1 : (C1 : text_read)))'	# nested documents
'}' )


write_sample_with_comment = (
'{'
	'(A1 : True)'
	'(A1 : False)'
	'(A2 : text_write)'
	'(A3 : num_match)'
	# '(A3 : geo_op)'		# do not exist
	# '(A3 : range_op)'		# do not exist
	'(A4 : Array.Bool)'		# write an array of boolean as a single element
	'(A4 : Array.Text)'
	'(A4 : Array.Num)'
	# '(A4 : arr_write_op)'	# do not exist
	'(A4 : arr_add_op.Bool)' 	# add an boolean item into a array.
	'(A4 : arr_add_op.Text)'
	'(A4 : arr_add_op.Num)'
	'(A4 : arr_remove_op.Bool)' 	# remove an boolean item into a array.
	'(A4 : arr_remove_op.Text)'
	'(A4 : arr_remove_op.Num)'
	'(A5 : (B1 : True)(B2 : text_write))'
	'(A5 : (B1 : (C1 : text_write)))'	# nested documents

'}' )

sort_sample = '''{
	(A1 : 1)
	(A2 : -1)
}
'''

absolute_uniform_sample = 'uniform(1000)' # case insensitive
absolute_normal_sample = 'Normal(0.1, 1000)' # Normal(sigma, total)


rule_sample = '''
RULE_ID: {
	{ (A1 : range_op) (A2 : False) },
	{ (A2: text_write) (A1 : arr_write_op.Num) },
	{},
	0 - 100 = Normal(0.1, 1000)
};
'''


ruleset_sample = '''{
	UPDATE_ALL: {
		ALL,
		{(A4 : Array.Text)},
		{},
		0 - 1000 = Uniform(1000)
	};
	DELETE: {
		{(A1 : True)},
		NULL,
		{},
		1001 - 2000 = Uniform(1000)
	};
	UPDATE: {
		{(A1 : False)},
		{(A4 : arr_write_op.Num)},
		{A4 : 1},
		0 - 2000 = Normal(0.1, 2000);
	};
}
'''


