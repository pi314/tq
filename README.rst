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

* ``d queue start`` - start a task queue for further ``pushq`` / ``pullq``
* ``d queue dump`` - dump queue content in JSON format
* ``d queue load`` - load queue content JSON format stdin before starting queue
* ``d queue`` - same as ``d queue start``
* ``d pushq`` - put task to queue and exit
* ``d pullq`` - put task to queue and exit

All other commands are directly passed to ``drive``.
