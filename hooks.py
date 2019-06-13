import sys

from os.path import basename
from threading import Thread

from .utils import log_info, log_error
from .utils import run
from .utils import send_telegram_msg


def pre_dummy(task):
    pass


def post_dummy(*args):
    pass


def pre_delete(task):
    task.cmd = 'trash'
    log_info('Remap "delete" to "trash"')


def pre_list(task):
    return True


def post_list(task, out, err):
    if err:
        log_error(err.decode('utf-8'), end="")
        return

    for line in sorted(out.decode('utf-8').rstrip('\n').split('\n')):
        line = line.rstrip()
        print(line)


def pre_push(task):
    task.cmd = {
            'pushq': 'push',
            'pullq': 'pull',
            }.get(task.cmd, task.cmd)

    task.args = ['-no-prompt', '-exclude-ops', 'delete'] + task.args


def post_push(task, out, err):
    try:
        if task.cmd.endswith('q'):
            t = Thread(target=send_telegram_msg, args=(task,))
            t.daemon = True
            t.start()
        else:
            send_telegram_msg(task)
    except KeyboardInterrupt:
        pass


def pre_rename(task):
    skip = True

    if len(task.args) != 2:
        print('Usage:')
        print('    d rename A B')
        sys.exit(1)

    task.args[1] = basename(task.args[1])
