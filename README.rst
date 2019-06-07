===============================================================================
dpush - a wrapper to `drive <https://github.com/odeke-em/drive>`_
===============================================================================
I want ``drive`` to

* Send Telegram notification after ``push`` finished
* Remap ``delete`` to ``trash`` so I won't accidentally destroy files
* Queue my ``push`` commands and do it one-by-one

None of those should be made into ``drive``, so here the wrapper comes!


Installation
-------------------------------------------------------------------------------
WIP


Usage
-------------------------------------------------------------------------------
Assume this utility is called by / soft-linked to / aliased to ``d``,

* ``d queue`` - start a task queue for further ``pushq`` / ``pullq``
* ``d queue`` - same as ``d queue start``
* ``d queue dump`` - dump queue content in an easy-to-read format
* ``d queue dumpjson`` - dump queue content in JSON format
* ``d queue load`` - load queue content from stdin before starting queue
* ``d queue quit`` - put a "stop" task into queue
* ``d pushq`` - put task to queue and exit
* ``d pullq`` - put task to queue and exit
* ``cat | d pullq`` - collect file names from stdin, every line is treated as a task
* ``d index`` - create two pure-text index files for remote and local content

  - Note: the usage and meaning of this command is different to ``drive index``

All other commands are directly passed to ``drive``.
