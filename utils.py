import re
import subprocess as sub
import sys

from os import getcwd
from os.path import exists, isfile, join, dirname
from subprocess import PIPE
from datetime import datetime


log_fname = None
log_file = None
log_cwd = None

telegram_bot = 'cychih_bot'


# =============================================================================
# Log utility
# -----------------------------------------------------------------------------
def log_create():
    global log_fname
    global log_cwd

    now = datetime.now()
    log_fname = 'dqueue.' + now.strftime('%Y%m%d_%H:%M:%S.') + '%06d'%(now.microsecond) +'.log'
    log_cwd = getcwd()


def log_write(*args):
    global log_fname
    global log_file

    if not log_fname:
        return

    if not log_file:
        log_file = open(join(log_cwd, log_fname), 'wb')

    log_file.write((' '.join(args).rstrip('\n') + '\n').encode('utf-8'))
    log_file.flush()


def log_info(*args, **kwargs):
    print(*args, **kwargs)
    log_write(*args)


def log_error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# -----------------------------------------------------------------------------
# Log utility
# =============================================================================


def get_drive_root(cwd=None):
    probe = cwd if cwd else getcwd()

    while probe != '/':
        if exists(join(probe, '.gd')) and isfile(join(probe, '.gd', 'credentials.json')):
            return probe

        probe = dirname(probe)

    return None


def run(cmd, capture_output=False):
    kwargs = {
        'stdout': sys.stdout,
        'stderr': sys.stderr,
    }
    if capture_output:
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE

    return sub.run(map(str, cmd), **kwargs)


def send_telegram_msg(task):
    run([telegram_bot, str(task)])
