import os
import sys

import atexit
import pathlib
import queue
import threading

import logging

from os.path import expanduser, exists

from . import channel
from .channel import TQServerCommand, TQServerCommandResult
from .config import TQ_DIR, TQ_PID_FILE
from .config import TQ_LOG_FNAME

logger = None

ss = None
bye = None


def read_pid_file():
    if not TQ_PID_FILE.exists():
        return
    try:
        with open(TQ_PID_FILE) as f:
            return int(f.read(), 10)
    except:
        return


def write_pid_file():
    TQ_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(TQ_PID_FILE, 'w') as f:
            f.write(f'{os.getpid()}\n')
    except:
        return


def del_pid_file():
    TQ_PID_FILE.unlink(missing_ok=True)
    try:
        TQ_DIR.unlink(missing_ok=True)
    except PermissionError:
        pass


def detect():
    pid = read_pid_file()
    if pid is None:
        return None

    if not channel.TQAddr(pid).file.exists():
        del_pid_file()
        return None

    return pid


def despawn():
    bye.set()
    ss.close()

    # import signal
    # os.kill(os.getpid(), signal.SIGINT)


def spawn():
    daemon_pid = read_pid_file()
    if daemon_pid is not None and daemon_pid != os.getpid():
        return daemon_pid

    try:
        r, w = os.pipe()
        pid = os.fork()
        if pid > 0:
            # exit first parent
            # readline() is necessary over read()
            try:
                return int(os.fdopen(r).readline().strip())
            except ValueError:
                return
    except OSError as e:
        sys.stderr.write(f'fork #1 failed: {e.errno} (e.strerror)\n')
        sys.exit(1)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f'fork #2 failed: {e.errno} (e.strerror)\n')
        sys.exit(1)

    write_pid_file()

    # read pid file back to make sure it's me
    daemon_pid = read_pid_file()
    if daemon_pid is not None and daemon_pid != os.getpid():
        onready(daemon_pid)
        sys.exit(1)

    def onexit():
        logging.info('onexit')
        del_pid_file()

    atexit.register(onexit)

    def onready():
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'w')
        se = open(os.devnull, 'w')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        logging.info(f'server ready')

        # newline is necessary
        os.write(w, f'{os.getpid()}\n'.encode('utf8'))

    boot(onready)


def boot(onready):
    global logger
    global bye

    from logging.handlers import RotatingFileHandler
    one_mb = 1024 * 1024
    logging.basicConfig(
            handlers=[RotatingFileHandler(
                filename=f'{TQ_DIR / TQ_LOG_FNAME}', maxBytes=one_mb, backupCount=5
                )],
            level=logging.INFO,
            datefmt='%Y-%m-%d %H:%M:%S',
            format=f'[%(asctime)s.%(msecs)03d][{os.getpid()}] %(message)s')

    logging.info('=' * 42)

    bye = threading.Event()

    logging.info('start frontdesk thread')
    t = threading.Thread(target=frontdesk, args=(onready,), daemon=True)
    t.start()

    try:
        t.join()
    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    logging.info('server quit')


def frontdesk(onready):
    logging.info('frontdesk ready')
    global ss

    ss = channel.TQServerSocket(os.getpid())

    try:
        with ss:
            onready()
            while not bye.is_set():
                conn = ss.accept()
                if conn:
                    logging.info('client connected')
                    try:
                        handle_client(conn)
                    except BrokenPipeError as e:
                        logging.info('client BrokenPipeError')
                    logging.info('client disconnected')

    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    logging.info('frontdesk bye')


def handle_client(conn):
    while not bye.is_set():
        cmd = conn.recv()
        if not cmd:
            break

        if not isinstance(cmd, TQServerCommand):
            logging.info(f'client {cmd}')
            conn.send(TQServerCommandResult(400))
            break

        logging.info(f'client cmd={cmd.cmd}')

        if cmd.cmd == 'despawn':
            despawn()

        elif cmd.cmd == 'echo':
            logging.info(f'server {cmd.cmd}, {cmd.args}, {cmd.kwargs}')
            conn.send(TQServerCommandResult(200, *cmd.args, **cmd.kwargs))

        else:
            logging.info(f'server 400 {cmd.cmd}')
            conn.send(TQServerCommandResult(400, cmd.cmd))
