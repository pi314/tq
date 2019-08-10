import sys

from os.path import basename, join

from . import telegram

from .logger import log_error
from .utils import get_drive_root


def pre_delete(task):
    task.cmd = 'trash'
    print('Remap "delete" to "trash"')


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
    args = []
    for a in task.args:
        if a.startswith('/'):
            args.append(join(get_drive_root(task.cwd), a[1:]))
        else:
            args.append(a)

    task.args = ['-no-prompt', '-exclude-ops', 'delete'] + args


def post_push(task, out, err):
    telegram.send_msg(str(task))


pre_pull = pre_push
post_pull = post_push


def pre_rename(task):
    if len(task.args) != 2:
        print('Usage:')
        print('    d rename A B')
        sys.exit(1)

    arg0 = task.args[0]
    if arg0.startswith('/'):
        task.args[0] = join(get_drive_root(task.cwd), arg0[1:])

    task.args[1] = basename(task.args[1])
