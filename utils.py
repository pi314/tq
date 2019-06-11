import re
import subprocess as sub
import sys

from os import getcwd
from os.path import exists, isfile, join, dirname
from subprocess import PIPE

from .chain import Chain


telegram_bot = 'cychih_bot'


def get_drive_root():
    probe = getcwd()

    while probe != '/':
        if exists(join(probe, '.gd')) and isfile(join(probe, '.gd', 'credentials.json')):
            return probe

        probe = dirname(probe)

    return None


def log_info(*args, **kwargs):
    if sys.stdout.isatty():
        print(*args, **kwargs)
    else:
        with open('/dev/tty', 'w') as tty:
            stdout_backup, sys.stdout = sys.stdout, tty
            print(*args, **kwargs, file=tty)
            sys.stdout = stdout_backup


def log_error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def run(cmd, capture_output=False):
    kwargs = {
        'stdout': sys.stdout,
        'stderr': sys.stderr,
    }
    if capture_output:
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE

    return sub.run(map(str, cmd), **kwargs)


def send_telegram_msg(cmd, argv, result, output):
    run([
        telegram_bot,
        '\n'.join(list(map(
            lambda x: '['+result+'] '+ x,
            [
                'pwd: '+ getcwd(),
                'cmd: '+ cmd
                ] + list(map(lambda x: 'arg: '+ x, argv))
        )))
    ])
