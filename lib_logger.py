import json
import sys

from os import getcwd
from os.path import join

from . import lib_config

from .models import *
from .lib_utils import *


log_fname = None
log_file = None
log_cwd = None


def log_create():
    global log_fname
    global log_cwd

    log_fname = lib_config.get('log', 'filename')
    log_cwd = getcwd()


def _log_write(entry):
    global log_fname
    global log_file

    if not log_fname:
        return

    if not log_file:
        log_file = open(join(log_cwd, log_fname), 'ab')

    now = datetime.now()
    entry['time'] = now.strftime('%Y%m%d_%H:%M:%S_') + '%06d'%(now.microsecond)

    log_file.write((json.dumps(entry).rstrip('\n') + '\n').encode('utf-8'))
    log_file.flush()


def print_error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def log_task(task):
    e = {
            'category': 'task',
            'tid': task.tid,
            'cwd': task.cwd,
            'cmd': task.cmd,
            'args': task.args,
            'block': task.block,
            'status': task.status,
    }

    if task.ret is not None:
        e['ret'] = task.ret

    _log_write(e)

    print()
    print(task)


def log_sys(status, reason):
    e = {
            'category': 'sys',
            'status': status,
            'reason': reason
    }

    _log_write(e)

    print()
    print('[status] {}: {}'.format(status, reason))
