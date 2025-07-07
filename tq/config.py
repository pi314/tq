import pathlib

from pathlib import Path

TQ_DIR = pathlib.Path.home() / Path('.tq')

TQ_PID_FILE = TQ_DIR / Path('tq.pid')

TQ_SOCKET_FILE_PREFIX = 'tq.socket.'
TQ_LOG_FILE_PREFIX = 'tq.log.'
