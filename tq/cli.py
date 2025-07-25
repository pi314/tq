import argparse
import sys
import os

import subprocess as sub
import threading
import queue

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
    print('  info       Print more detailed information about the task')
    print('  cat        Print stdout file of specified tasks, block until the tasks finish')
    print('  head       (WIP)')
    print('  tail       (WIP)')
    print('  wait       Wait for specified tasks to finish')
    print('  cancel     Cancel a task if it\'s not started yet')
    print('  kill       Kill specified tasks')


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

    elif argv[0] in ('info',):
        handle_info(argv[1:])

    elif argv[0] in ('cat',):
        handle_cat(argv[1:])

    elif argv[0] in ('wait',):
        handle_wait(argv[1:])

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

    lines = []
    lines.append(('task_id', 'status', 'cmd'))
    for msg in tq_api.list(task_id_list):
        if msg.res >= 200:
            break
        import shlex
        lines.append((str(msg.task_id), msg.status, shlex.join(msg.cmd)))

    width = [0 for col in lines[0]]
    for line in lines:
        width = [max(width[i], len(line[i])) for i in range(3)]

    for line in lines:
        print(line[0].rjust(width[0]) +'  '+ line[1].ljust(width[1]) +'  '+ line[2].ljust(width[2]))


def handle_block(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    msg = tq_api.block()
    print(msg)


def handle_unblock(argv, count=None):
    conn = connect()
    if not conn:
        sys.exit(1)

    msg = tq_api.unblock(count=count)
    print(msg)


def handle_info(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    import shlex
    for idx, msg in enumerate(tq_api.list([int(arg) for arg in argv])):
        if msg.res >= 200:
            break
        if idx:
            print()
        print(f'Task_id   : {msg.task_id}')
        print(f'Cwd       : {msg.cwd}')
        print(f'Command   : {shlex.join(msg.cmd)}')
        print(f'Returncode: {msg.returncode}')
        print(f'Status    : {msg.status}')
        print(f'stdout    : {msg.stdout}')
        print(f'stderr    : {msg.stderr}')


def handle_cat(argv):
    conn = connect(spawn=True)
    if not conn:
        sys.exit(1)

    # Verify task_id list
    task_id_list = [int(arg) for arg in argv]
    forever = not task_id_list

    # Receive task events from server
    desk_lock = threading.Lock()
    desk = {}
    update_num = threading.Semaphore(0)

    def task_event_handler(msg):
        from .tq_api import TQEvent
        if not isinstance(msg, TQEvent):
            task_id_list.append(None)
            update_num.release()
            return False
        if msg.event != 'task':
            return

        with desk_lock:
            desk[msg.task_id] = (msg.stdout, msg.status)
            if forever:
                if msg.status in ('start', 'running'):
                    task_id_list.append(msg.task_id)
            update_num.release()

    monitor_thread = tq_api.subscribe(task_event_handler, finished=bool(task_id_list))

    def cat(task_id):
        if task_id not in desk:
            return False

        with open(desk[task_id][0], 'rb') as f:
            while True:
                data = f.read()
                if data:
                    sys.stdout.buffer.write(data)
                    sys.stdout.flush()
                    continue

                with desk_lock:
                    if desk[task_id][1] in ('finished', 'error'):
                        break

                import time
                time.sleep(0.1)

    # Schedule next stdout file
    skip_finished = forever
    while True:
        update_num.acquire()
        with desk_lock:
            if not task_id_list:
                if forever:
                    continue
                else:
                    break

            task_id = task_id_list[0]
            if task_id is None:
                break
            if task_id not in desk:
                continue
            if skip_finished and desk[task_id][1] in ('finished', 'error'):
                task_id_list.pop(0)
                continue
            skip_finished = False

        cat(task_id)
        task_id_list.pop(0)

        with desk_lock:
            if not task_id_list:
                if forever:
                    continue
                else:
                    break

    conn.close()
    monitor_thread.join()


def handle_wait(argv):
    conn = connect(spawn=True)
    if not conn:
        sys.exit(1)

    if not argv:
        print('Which tasks to wait?')
        sys.exit(1)

    # Verify task_id list
    task_id_list = set(int(arg) for arg in argv)

    # Receive task events from server
    desk_lock = threading.Lock()
    update_num = threading.Semaphore(0)

    def task_event_handler(msg):
        from .tq_api import TQEvent
        if not isinstance(msg, TQEvent):
            update_num.release()
            return False
        if msg.event != 'task':
            return

        with desk_lock:
            if msg.status in ('finished', 'error'):
                task_id_list.discard(msg.task_id)
            update_num.release()

    monitor_thread = tq_api.subscribe(task_event_handler, finished=True)

    # Schedule next stdout file
    while True:
        update_num.acquire()
        with desk_lock:
            if not task_id_list:
                break

    conn.close()
    monitor_thread.join()


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
    print(res, res.args)
