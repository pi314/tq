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

* ``d pushw`` - wait for previous existing ``d`` finishes before push
* ``d wait`` - wait for all ``d`` processes to finish
* ``d tickets`` - show all ``d`` ticket files

All other commands are directly passed to ``drive``.
