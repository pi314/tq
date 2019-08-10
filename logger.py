import json
import sys

from os import getcwd
from os.path import join


log_fname = None
log_file = None
log_cwd = None


def log_create():
    global log_fname
    global log_cwd

    log_fname = 'tq.log'
    log_cwd = getcwd()


def log_write(*args):
    global log_fname
    global log_file

    if not log_fname:
        return

    if not log_file:
        log_file = open(join(log_cwd, log_fname), 'ab')

    log_file.write((' '.join(args).rstrip('\n') + '\n').encode('utf-8'))
    log_file.flush()


def log_info(*args, **kwargs):
    print(*args, **kwargs)
    log_write(*args)


def log_error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def log_dict(j):
    log_write(json.dumps(j))


def log_task_status(task, returncode=None):
    e = task.to_dict()
    e['status'] = task.status

    if task.ret is not None:
        e['ret'] = task.ret

    log_dict(e)

    print()
    print(str(task))
