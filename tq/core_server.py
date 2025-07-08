import os
import sys

import atexit
import pathlib
import queue
import threading

from os.path import expanduser, exists

from . import core_channel
from .config import TQ_DIR, TQ_PID_FILE
from .config import TQ_LOG_FILE_PREFIX

logger = None

ss = None
Q = None
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

    if not core_channel.TQAddr(pid).file.exists():
        del_pid_file()
        return None

    return pid


def stop():
    bye.set()
    Q.put(None)
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
        logger.info('onexit')
        del_pid_file()

    atexit.register(onexit)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'w')
    se = open(os.devnull, 'w')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    def onready():
        logger.info('server ready')

        # newline is necessary
        os.write(w, f'{os.getpid()}\n'.encode('utf8'))

    boot(onready)


def boot(onready):
    global logger
    global Q
    global bye

    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename=f'{TQ_DIR / TQ_LOG_FILE_PREFIX}{os.getpid()}', level=logging.INFO,
                        format='[%(asctime)s] %(message)s')

    logger.info(f'logger ready, pid={os.getpid()}')

    bye = threading.Event()

    Q = queue.Queue()

    logger.info('start worker thread')
    t1 = threading.Thread(target=worker, daemon=True)
    t1.start()

    logger.info('start listener thread')
    t2 = threading.Thread(target=listener, args=(onready,), daemon=True)
    t2.start()

    t1.join()
    t2.join()

    logger.info('server quit')


def listener(onready):
    global ss

    ss = core_channel.create_server_socket(os.getpid())

    try:
        with ss:
            onready()

            while not bye.is_set():
                conn = ss.accept()
                Q.put(conn)

    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logger.exception(e)

    logger.info('listener bye')


def worker():
    try:
        while not bye.is_set():
            conn = Q.get()
            if conn:
                handle_client(conn)

    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logger.exception(e)

    logger.info('worker bye')


def handle_client(conn):
    logger.info('client helo')
    conn.send('[helo]')
    while True:
        data = conn.recv()
        if not data:
            break

        logger.info(f'client {data}')

        if data == 'stop':
            conn.send('bye')
            stop()

        elif data == 'pid':
            logger.info(f'pid {pid}')
            conn.send(f'{pid}')

        else:
            logger.info(f'server {data}')
            conn.send(f'[{data}]')

    logger.info('client bye')
