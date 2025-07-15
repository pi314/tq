import argparse
import sys
import os

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
    print('  list / ls  Show ')


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

    elif argv[0] in ('quit', 'shutdown'):
        handle_shutdown(argv[1:])

    elif argv[0] in ('list', 'ls'):
        handle_list(argv[1:])

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


def handle_shutdown(argv):
    conn = connect()
    if conn:
        res = tq_api.shutdown()
        print(res)


def handle_list(argv):
    conn = connect()
    if conn:
        for res in tq_api.list():
            print(res, res.args)


def handle_kill(argv, soft=False):
    conn = connect()
    if conn:
        res = tq_api.cancel(args.cmd[1])
        print(res)


def handle_shell(argv):
    conn = connect(spawn=True)
    if conn:
        res = tq_api.enqueue(argv)
        print(res)
