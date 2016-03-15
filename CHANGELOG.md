## 2016-03-14

Main:

- improve memory efficiency by saving session into temporary date file.
- add a better help message in `--show` and `--showid`.
- drop `--drop` arguments in main function.
- save sessions file from executor.

Parser:

- add better method name

Executor:

- **new feature**: display execution result after `run()`
- add `histtype` in config.ini, to configure diagram type.
- add time scale factor
- add a 3 seconds delay in whole execution.
- add method `get_session_queue`

Bugfixs:

- parser:

	* time in time interval should be integer. 
	
- main

	* force to connect to database during initialization, in order to make sure the connection is valid.



## 2016-03-01

Initial beta version