import os
import sys

import queue
import threading

import logging

from os.path import expanduser, exists

from . import daemon
from . import channel
from .channel import TQServerCommand, TQServerCommandResult
from .config import TQ_DIR, TQ_LOG_FNAME

ss = None
bye = None


def spawn():
    daemon_pid = daemon.read_pid_file()
    if daemon_pid is not None and daemon_pid != os.getpid():
        return daemon_pid

    ret = daemon.spawn()
    if isinstance(ret, int) or ret is None:
        return ret

    onready = ret
    boot(onready)


def despawn():
    bye.set()
    ss.close()

    # import signal
    # os.kill(os.getpid(), signal.SIGINT)


def boot(onready):
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

    logging.info('start worker thread')
    t1 = threading.Thread(target=worker_thread, daemon=True)
    t1.start()

    logging.info('start frontdesk thread')
    t2 = threading.Thread(target=frontdesk_thread, args=(onready,), daemon=True)
    t2.start()

    try:
        t1.join()
        t2.join()
    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    logging.info('server quit')
    sys.exit(0)


def frontdesk_thread(onready):
    logging.info('frontdesk thread start')
    global ss

    ss = channel.TQServerSocket(os.getpid())

    try:
        with ss:
            onready(os.getpid())
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

    logging.info('frontdesk thread bye')


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


def worker_thread():
    logging.info('worker thread start')
    logging.info('worker thread bye')
