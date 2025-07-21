import argparse
import sys
import os

import subprocess as sub

from os.path import basename

from . import __version__
from . import tq_api


_verbose = False


def verbose(*args, **kwargs):
    if _verbose:
        print(*args, **kwargs)


def handle_brief_help(argv):
    def print(*args, **kwargs):
        import builtins
        kwargs['file'] = sys.stderr
        builtins.print(*args, **kwargs)

    print('Usage:')
    print('$ tq -h / --help / help')
    print('$ tq --version / version')


def handle_help(argv):
    def print(*args, **kwargs):
        import builtins
        kwargs['file'] = sys.stderr
        builtins.print(*args, **kwargs)

    print('tq - task queue')
    print()
    print('Subcommands:')
    print('  help       Show this message and exit')
    print('  version    Show tq version and exit')
    print('  pid        Show the pid of tq server')
    print('  shutdown   Shutdown tq server')
    print('  quit       Alias to shutdown')
    print('  list       Show task queue')
    print('  block      Pending to consume queued tasks')
    print('  unblock    Continue to consume queued tasks')
    print('  step       Consume one queued task (if any) and continue to block')
    print('  cat        (WIP)')
    print('  head       (WIP)')
    print('  tail       (WIP)')
    print('  cancel     Cancel a task if it\'s not started yet')
    print('  kill       Kill a task')


def main():
    global _verbose
    prog = basename(sys.argv[0])
    argv = sys.argv[1:]

    # Parse options
    if argv and argv[0] in ('-v', '--verbose'):
        _verbose = True
        argv.pop(0)

    # Parse sub-commands
    if not argv:
        tq_api.spawn()
        handle_list([])

    elif argv[0] in ('--version',):
        handle_version(argv[1:], brief=True)

    elif argv[0] in ('version',):
        handle_version(argv[1:], brief=False)

    elif argv[0] in ('-h',):
        handle_brief_help(argv[1:])

    elif argv[0] in ('--help', 'help'):
        handle_help(argv[1:])

    elif argv[0] in ('pid',):
        handle_pid(argv[1:])

    elif argv[0] in ('quit', 'shutdown'):
        handle_shutdown(argv[1:])

    elif argv[0] in ('list',):
        handle_list(argv[1:])

    elif argv[0] in ('block',):
        handle_block(argv[1:])

    elif argv[0] in ('unblock',):
        handle_unblock(argv[1:])

    elif argv[0] in ('step',):
        handle_unblock(argv[1:], count=1)

    elif argv[0] in ('cat',):
        handle_cat(argv[1:])

    elif argv[0] in ('head', 'tail'):
        print('WIP')
        sys.exit(1)

    elif argv[0] in ('cancel',):
        handle_kill(argv[1:], soft=True)

    elif argv[0] in ('kill',):
        handle_kill(argv[1:], soft=False)

    elif argv[0] in ('--', 'shell'):
        handle_shell(argv[1:])

    else:
        handle_shell(argv)


def connect(spawn=False):
    verbose(f'os.getpid() = {os.getpid()}')

    conn = tq_api.connect(spawn=spawn)
    if not conn:
        print('Cannot connect to tq server')
        sys.exit(1)

    verbose(f'tq server pid = {conn.pid}')
    return conn


def handle_version(argv, brief=False):
    if brief:
        print(f'{__version__}')
    else:
        print(f'tq {__version__} - a task queue system.')
        print('Copyright (C) 2025-2025  Chang-Yen Chih')
    sys.exit()


def handle_pid(argv):
    tq_pid = tq_api.detect()
    if not tq_pid:
        sys.exit(1)
    print(tq_pid)


def handle_shutdown(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    res = tq_api.shutdown()
    print(res)


def handle_list(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    task_id_list = [int(arg) for arg in argv]

    for res in tq_api.list(task_id_list):
        print(res, res.args)


def handle_block(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    res = tq_api.block()
    print(res)


def handle_unblock(argv, count=None):
    conn = connect()
    if not conn:
        sys.exit(1)

    res = tq_api.unblock(count=count)
    print(res)


def handle_cat(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    tail_proc = None

    def handle_server_event(msg):
        nonlocal tail_proc
        from .tq_api import TQEvent
        if not isinstance(msg, TQEvent):
            return False

        if msg.args['status'] == 'start':
            if tail_proc:
                tail_proc.kill()
            tail_proc = sub.Popen(['tail', '-f', msg.args['stdout']])

    t = tq_api.subscribe(handle_server_event)
    t.join()


def handle_kill(argv, soft=False):
    conn = connect()
    if not conn:
        sys.exit(1)

    res = tq_api.cancel(args.cmd[1])
    print(res)


def handle_shell(argv):
    if argv[0].startswith('-'):
        print(f'Unknown command: "{argv[0]}"', file=sys.stderr)
        sys.exit(1)

    conn = connect(spawn=True)
    if not conn:
        sys.exit(1)

    res = tq_api.enqueue(argv)
    print(res)
