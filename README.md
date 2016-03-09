# NoWog (Not only Workload Generator)

NoWog is a workload generator able to generate and execute customizable MongoDB workload based on a specific input format defined in **doc/EBNF_gammar.txt**.

NoWog consist of three parts:

1. **Parser**: use pyparsing to parse the BNF input. Parser result consist of ID of each rule, distribution and operation information.

2. **Mapping**: map the parser result into MongoDB command.

	This part use **distribution.py** to draw sampled from specified distribution. And use **values.py** to generate all random values in each command. Each rule will be mapped as a session, which consist of its ID and a execution time table.

3. **Execution**: execute all sessions. This part are also able to display histogram of specific type or IDs of workload.



## Usage without scenarios:


1. Read and edit all settings in **config.ini**:


2. Run **main.py** with or without arguments:

	**Example**:

	- If run without any arguments, program will exit after generate (or write) sessions file.
        
		``` $ python main.py```
	
	- Display workload histogram for all operations of all sessions.
        
		``` $ python main.py --show```

	- Only run one operation in each session once, in order to test the correctness and runnability of the generated command.

		``` $ python main.py --try```

	- Run all operations in all sessions under prearranged distribution.

		``` $ python main.py --run```

## Usage with scenarios:


1. Read and edit all settings in **scenario.ini**:

2. Run **scenario.py** without any arguments



## Dependencies


Python version: higher than 2.7

MongoDB version: 3.2.1

Require modules:

- pymongo
- pyparsing
