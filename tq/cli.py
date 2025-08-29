import argparse
import sys
import os
import re
import time

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
    print()
    print('  Informative')
    print('    help       Show this message and exit')
    print('    version    Show tq version and exit')
    print('    pid        Show the pid of tq server')
    print('    shutdown   Shutdown tq server')
    print('    quit       =shutdown')
    print()
    print('  Queue Monitoring')
    print('    list       Show task queue')
    print('    info       Print more detailed information about the task')
    print('    cat        Print stdout file of specified tasks, block until the tasks finish')
    print()
    print('  Queue Management')
    print('    block      Pending to consume queued tasks')
    print('    unblock    Continue to consume queued tasks')
    print('    step       Consume one queued task (if any) and continue to block')
    print('    urgent     Make specified pending task urgent, move to the beginning of pending queue')
    print('    up         Move specified pending task up')
    print('    down       Move specified pending task down')
    print()
    print('  Task Management')
    print('    cancel     Cancel specified pending tasks')
    print('    kill       Kill specified tasks, or the current running task if not specified')
    print('    wait       Wait for specified tasks to finish, or the current running task if not specified')
    print('    clear      Clear information of specified tasks, or all finished tasks if not specified')
    print('    retry      Re-schedule specified task into pending queue')


def format_time(t):
    if t is None:
        return 'None'
    return time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(t))


def format_time_delta(t):
    if t is None:
        return 'None'

    t = int(t)
    secs = t % 60
    mins = (t // 60) % 60
    hours = (t // 3600) % 24
    days = (t // 3600) // 24
    parts = []
    if days:
        parts.append(f'{days} days')
    if hours:
        parts.append(f'{hours} hours')
    if mins:
        parts.append(f'{mins} mins')
    if secs:
        parts.append(f'{secs} secs')
    return ' '.join(parts)


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
        handle_()

    elif argv[0] == '--version':
        handle_version(argv[1:], brief=True)

    elif argv[0] == 'version':
        handle_version(argv[1:], brief=False)

    elif argv[0] == '-h':
        handle_brief_help(argv[1:])

    elif argv[0] in ('--help', 'help'):
        handle_help(argv[1:])

    elif argv[0] == 'pid':
        handle_pid(argv[1:])

    elif argv[0] == 'status':
        handle_status(argv[1:])

    elif argv[0] in ('quit', 'shutdown'):
        handle_shutdown(argv[1:])

    elif argv[0] == 'list':
        handle_list(argv[1:])

    elif argv[0] == 'block':
        handle_block(argv[1:])

    elif argv[0] == 'unblock':
        handle_unblock(argv[1:])

    elif argv[0] == 'step':
        handle_unblock(argv[1:], count=1)

    elif argv[0] == 'urgent':
        handle_urgent(argv[1:])

    elif argv[0] == 'up':
        handle_up(argv[1:])

    elif argv[0] == 'down':
        handle_down(argv[1:])

    elif argv[0] == 'info':
        handle_info(argv[1:])

    elif argv[0] == 'cat':
        handle_cat(argv[1:])

    elif argv[0] == 'wait':
        handle_wait(argv[1:])

    elif argv[0] == 'cancel':
        handle_cancel(argv[1:])

    elif argv[0] == 'kill':
        handle_kill(argv[1:])

    elif argv[0] == 'clear':
        handle_clear(argv[1:])

    elif argv[0] == 'retry':
        handle_retry(argv[1:])

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


def handle_():
    tq_pid = tq_api.detect()
    if not tq_pid:
        tq_pid = tq_api.spawn()
        print(tq_pid)
        sys.exit()

    handle_list([])


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


def handle_status(argv):
    conn = connect()
    if not conn:
        print('Cannot connect to tq server')
        sys.exit(1)

    msg = tq_api.status()
    print(f'pid: {msg.args.pid}')
    print(f'blocking: {msg.args.time_to_block is not None}')
    if msg.args.time_to_block:
        print(f'Time to block: {msg.args.time_to_block}')
    print(f'Boot time: {format_time(msg.args.boot_time)}')

    print(f'Up time: {format_time_delta(time.time() - msg.args.boot_time)}')

    print()
    print(f'Finshed: {msg.args.finished}')
    print(f'Running: {int(msg.args.running)}')
    print(f'Pending: {msg.args.pending}')


def handle_shutdown(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    tq_api.shutdown()
    print('bye')


def handle_list(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    task_id_list = [int(arg) for arg in argv]

    lines = []
    lines.append(('id', 'status', 'cmd'))
    msg = tq_api.list(task_id_list)
    for info in msg.args:
        import shlex
        try:
            if info.status in ('running', 'pending', 'canceled', 'error'):
                status = info.status
            else:
                status = f'{info.returncode}'
            lines.append((str(info.task_id), status, shlex.join(info.cmd)))
        except:
            lines.append((str(info.task_id), '404', ''))

    width = [0 for col in lines[0]][::-1]
    for line in lines:
        width = [max(width[i], len(line[i])) for i in range(len(width))]

    for line in lines:
        print(f'{line[0].rjust(width[0])}  {line[1].ljust(width[1])}  {line[2]}')


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


def handle_urgent(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    if not argv or len(argv) > 1:
        sys.exit(1)

    msg = tq_api.urgent(int(argv[0], 10))
    print(msg)


def handle_up(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    if not argv or len(argv) > 1:
        sys.exit(1)

    msg = tq_api.up(int(argv[0], 10))
    print(msg)


def handle_down(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    if not argv or len(argv) > 1:
        sys.exit(1)

    msg = tq_api.down(int(argv[0], 10))
    print(msg)


def handle_info(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    import shlex
    msg = tq_api.list([int(arg) for arg in argv])
    for idx, info in enumerate(msg.args):
        if idx:
            print()

        try:
            lines = []
            lines.append(f'task id : {info.task_id}')
            lines.append(f'pid     : {info.pid}')
            lines.append(f'cwd     : {info.cwd}')
            lines.append(f'command : {shlex.join(info.cmd or [])}')
            lines.append(f'return  : {info.returncode}')
            lines.append(f'status  : {info.status}')
            lines.append(f'stdout  : {info.stdout}')
            lines.append(f'stderr  : {info.stderr}')

            if not info.start_time:
                duration = None
            elif not info.end_time:
                duration = time.time() - info.start_time
            else:
                duration = info.end_time - info.start_time
            lines.append(f'start   : {format_time(info.start_time)}')
            lines.append(f'end     : {format_time(info.end_time)} ({format_time_delta(duration)})')
            if 'error' in info:
                lines.append(f'error   : {info.error}')
            for line in lines:
                print(line)
        except Exception as e:
            print(f'task id : {info.task_id}')
            print(f'error   : {repr(e)}')


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
    bye = threading.Event()

    def task_event_handler(msg):
        from .tq_api import TQEvent
        if not isinstance(msg, TQEvent):
            task_id_list.append(None)
            bye.set()
            update_num.release()
            return False
        if msg.event != 'task':
            return

        with desk_lock:
            desk[msg.args.task_id] = (msg.args.stdout, msg.args.status)
            if forever:
                if msg.args.status in ('start', 'running'):
                    task_id_list.append(msg.args.task_id)
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

                if bye.is_set():
                    break

                with desk_lock:
                    if desk[task_id][1] in ('finished', 'error', 'canceled'):
                        break

                time.sleep(0.1)

    # Schedule next stdout file
    skip_finished = forever
    try:
        while True:
            update_num.acquire()
            if bye.is_set():
                break

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

    except:
        sys.exit(1)
    finally:
        conn.close()
        monitor_thread.join()


def handle_wait(argv):
    conn = connect(spawn=True)
    if not conn:
        sys.exit(1)

    task_id_list = set()
    if not argv:
        msg = tq_api.list()
        for info in msg.args:
            if info.status in ('running', 'pending'):
                task_id_list = set([info.task_id])
                break
        if not task_id_list:
            print('No running tasks to wait')
            sys.exit(1)
    else:
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
            if msg.args.status in ('finished', 'error'):
                task_id_list.discard(msg.args.task_id)
            update_num.release()

    monitor_thread = tq_api.subscribe(task_event_handler, finished=True)

    # Schedule next stdout file
    try:
        while True:
            update_num.acquire()
            with desk_lock:
                if not task_id_list:
                    break
    except:
        sys.exit(1)
    finally:
        conn.close()
        monitor_thread.join()


def handle_cancel(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    task_id_list = [int(arg) for arg in argv]
    msg = tq_api.cancel(task_id_list)
    for info in msg.args:
        print(f'{info.task_id}: {info.result}')

    if not msg.args:
        print('No tasks to cancel')

    if msg.res >= 400:
        sys.exit(1)


def handle_kill(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    task_id_list = []
    signal = None
    for arg in argv:
        m = re.fullmatch(r'-([0-9]+)', arg)
        if m:
            signal = int(m.group(1), 10)
            continue

        m = re.fullmatch(r'([0-9]+)', arg)
        if m:
            task_id_list.append(int(m.group(1), 10))

    res = tq_api.kill(task_id_list, signal=signal)
    print(res, res.args)


def handle_clear(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    task_id_list = set(int(arg) for arg in argv)
    msg = tq_api.clear(task_id_list)
    for info in msg.args:
        print(f'{info.task_id}: {info.result}')

    if not msg.args:
        print('No tasks to clear')

    if msg.res >= 400:
        sys.exit(1)


def handle_retry(argv):
    conn = connect()
    if not conn:
        sys.exit(1)

    task_id_list = [int(arg) for arg in argv]
    msg = tq_api.retry(task_id_list)
    for info in msg.args:
        print(f'{info.task_id}: {info.result}')

    if not msg.args:
        print('No tasks to clear')

    if msg.res >= 400:
        sys.exit(1)


def handle_shell(argv):
    if argv[0].startswith('-'):
        print(f'Unknown command: "{argv[0]}"', file=sys.stderr)
        sys.exit(1)

    conn = connect(spawn=True)
    if not conn:
        sys.exit(1)

    res = tq_api.enqueue(argv)
    print(res, res.args)
