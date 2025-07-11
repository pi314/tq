import pathlib

from pathlib import Path

TQ_DIR = pathlib.Path.home() / Path('.tq')

TQ_PID_FILE = TQ_DIR / Path('tq.pid')

TQ_LOG_FNAME = 'tq.server.log'

TQ_SOCKET_FILE_PREFIX = 'tq.socket.'
