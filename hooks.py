import shutil
import sys

from os.path import dirname, basename, join, exists, isdir

from . import lib_telegram

from .lib_logger import print_error
from .lib_utils import get_drive_root
from .models import Task


def expand_gpath(cwd, gpath):
    if gpath.startswith('/'):
        return join(get_drive_root(cwd), gpath[1:])

    return gpath


def pre_delete(task):
    task.args[0] = 'trash'
    print('Remap "delete" to "trash"')


def pre_list(task):
    task.cap_out = True


def post_list(task, out, err):
    if err:
        print_error(err.decode('utf-8'), end="")
        return

    for line in sorted(out.decode('utf-8').rstrip('\n').split('\n')):
        line = line.rstrip()
        print(line)


def pre_push(task):
    args = []
    for a in task.args[1:]:
        args.append(expand_gpath(task.cwd, a))

    stdin_lines = []
    if not sys.stdin.isatty():
        for line in sys.stdin.readlines():
            line = line.strip()
            stdin_lines.append(expand_gpath(task.cwd, line))

    args = [task.args[0], '-no-prompt', '-exclude-ops', 'delete'] + args

    if not len(stdin_lines):
        task.args = args
    else:
        ret = []
        for line in stdin_lines:
            t = task.copy()
            t.args = args + [line]
            ret.append(t)

        return ret


def post_push(task, out, err):
    if '-h' in task.args:
        return

    if task.block in (Task.LOCAL, Task.BLOCK):
        lib_telegram.send_msg(str(task))
    else:
        lib_telegram.notify_msg(str(task))


pre_pull = pre_push
post_pull = post_push


def pre_pushq(task):
    task.block = Task.QUEUE
    return pre_push(task)

post_pushq = post_push


def pre_pullq(task):
    task.block = Task.QUEUE
    return pre_pull(task)

post_pullq = post_pull


def pre_pushw(task):
    task.block = Task.BLOCK
    return pre_push(task)

post_pushw = post_push


def pre_pullw(task):
    task.block = Task.BLOCK
    return pre_pull(task)

post_pullw = post_pull


def pre_rename(task):
    if len(task.args) != 3:
        print('Usage:')
        print('    d rename A B')
        exit(1)

    task.args[1] = expand_gpath(task.cwd, task.args[1])
    task.args[2] = basename(task.args[2])

    folder = dirname(task.args[1])
    src = basename(task.args[1])
    dst = basename(task.args[2])
    print('[d rename] folder = {b[0]}\033[1;35m{f}\033[m{b[1]}'.format(f=folder, b='[]' if folder else '()'))
    print('[d rename] src = [\033[1;35m{}\033[m]'.format(src))
    print('[d rename] dst = [\033[1;35m{}\033[m]'.format(dst))


def pre_renameq(task):
    task.block = Task.QUEUE
    return pre_rename(task)


def post_rename(task, out, err):
    if len(task.args) == 3:
        folder = dirname(task.args[1])
        src = task.args[1]
        dst = join(folder, basename(task.args[2]))
        if exists(src) and not exists(dst):
            print('[rename] folder = {b[0]}\033[1;35m{f}\033[m{b[1]}'.format(f=folder, b='[]' if folder else '()'))
            print('[rename] src = [\033[1;35m{}\033[m]'.format(src))
            print('[rename] dst = [\033[1;35m{}\033[m]'.format(dst))


def pre_mv(task):
    dst = task.args[-1]

    task_list = []
    for src in task.args[1:-1]:
        print('[d mv] src = [\033[1;35m{}\033[m]'.format(src))
        print('[d mv] dst = [\033[1;35m{}\033[m]'.format(dst))
        task_list.append(Task(
            tid=Task.gen_tid(),
            cwd=task.cwd,
            cmd=task.cmd,
            args=['mv', src, dst],
            block=False,
            ))

    return task_list


def post_mv(task, out, err):
    if len(task.args) == 3:
        src_fpath = task.args[1]
        src_fname = basename(src_fpath)
        dst = task.args[2]
        dst_fpath = join(dst, src_fname)
        if exists(src_fpath) and isdir(dst) and not exists(dst_fpath):
            print('[mv] src = [\033[1;35m{}\033[m]'.format(src_fpath))
            print('[mv] dst = [\033[1;35m{}\033[m]'.format(dst_fpath))
            shutil.move(src_fpath, dst_fpath)

post_move = post_mv
