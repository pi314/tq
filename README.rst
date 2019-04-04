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

* ``d push`` - just push directly like ``drive push``
* ``d server`` - start a central queue server for local requests
* ``d pushq`` - queue the push command to the server and exit directly

  - May need a way to remove the command from queue

* ``d pushw`` - wait for previous existing ``d`` finishes before push

Not sure if those are easy to implement.
