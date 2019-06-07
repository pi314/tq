import re
import subprocess as sub
import sys
import os

from subprocess import PIPE
from datetime import datetime
from os.path import exists, join

from .chain import Chain


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
        '\n'.join(['pwd: '+ os.getcwd(), cmd +' '+ result +':'] + argv)
    ])
