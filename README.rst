===============================================================================
tq - a task queue specialized to `drive <https://github.com/odeke-em/drive>`_
===============================================================================
I want ``drive`` to

* Send Telegram notification after ``push`` finished
* Remap ``delete`` to ``trash`` so I won't accidentally destroy files
* Queue my ``push`` and ``pull`` commands and do them one-by-one

None of those should be made into ``drive``, so here the wrapper comes!

Important note: Please treat it as unstable before I give it a version number.
I've accidentally deleted my files more than one time, thankfully they are
either in Google drive's trash can, or they are not important (Yes some of them
are wiped out on my disk, before I push them to Google drive.)


Related Works
-------------------------------------------------------------------------------
* http://vicerveza.homeunix.net/~viric/soft/ts/

  - It seems a good replacement of this project; Have a look to it before using mine.
  - Maybe I'll change ``dpush`` as a wrapper to it if it's useful to me.


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
* [broken] ``cat | d pull`` - collect file names from stdin, every line is treated as a task
* [broken] ``cat | d pullq`` - collect file names from stdin, every line is treated as a task
* ``d index`` - create two pure-text index files for remote and local content
* ``d rename A B`` - rename ``A`` to ``B``, ``B`` will be processed by ``basename()``

  - Note: the usage and meaning of this command is different to ``drive index``

* [TODO] ``d help``

For ``push`` / ``pull`` / ``pushq`` / ``pullq`` / ``rename``, absolute paths will be
translated to relative path from the google drive root folder.

All other commands are directly passed to ``drive``.


Architecture
-------------------------------------------------------------------------------

::

  .---------------------------------------------------------------------------.
  |                                                                           |
  |  @---.                                                                    |
  |      |                                                                    |
  |  .----------.                                                             |
  |  | cli_main |                                                             |
  |  '----------'                                                 .--------.  |
  |      |                                                        | models |  |
  |      |------------.          .----------------.               '--------'  |
  |      |            |          | telegram_queue |        .---------------.  |
  |  .--------.   .-------.      '----------------'        | lib_drive_cmd |  |
  |  | cli_tq |   | cli_d |          |                     '---------------'  |
  |  '--------'   '-------'      .------------.             .--------------.  |
  |      |            |          | task_queue |             | lib_telegram |  |
  |      |------------'          '------------'             '--------------'  |
  |      | tq_cmd                    | tq_cmd                 .------------.  |
  |      |                           |                        | lib_logger |  |
  |  .-------------.             .-------------.              '------------'  |
  |  | wire_client |             | wire_server |               .-----------.  |
  |  '-------------'             '-------------'               | lib_utils |  |
  |      |                           |                         '-----------'  |
  |      '---------------------------'                        .------------.  |
  |             local TCP socket                              | lib_config |  |
  |                                                           '------------'  |
  |              .----------.                                                 |
  |              | lib_wire |                                                 |
  |              '----------'                                                 |
  '---------------------------------------------------------------------------'

On the server side, task_queue runs in the main thread,
and telegram_queue and wire_server are in daemon threads.

models contains class definition.
