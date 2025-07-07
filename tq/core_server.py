import os
import sys

import atexit
import pathlib

from os.path import expanduser, exists

from . import core_channel
from .config import TQ_DIR, TQ_PID_FILE
from .config import TQ_LOG_FILE_PREFIX


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


def spawn():
    import sys

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
        ready(daemon_pid)
        sys.exit(1)

    atexit.register(del_pid_file)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'w')
    se = open(os.devnull, 'w')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    def ready(pid):
        # newline is necessary
        os.write(w, f'{pid}\n'.encode('utf8'))

    serve(lambda: ready(os.getpid()))


def serve(ready_callback):
    pid = os.getpid()
    ss = core_channel.create_server_socket(pid)

    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename=f'{TQ_DIR / TQ_LOG_FILE_PREFIX}{pid}', level=logging.INFO,
                        format='[%(asctime)s] %(message)s')

    with ss:
        logger.info(f'server start {pid}')
        ready_callback()

        try:
            while True:
                conn = ss.accept()
                logger.info('client helo')
                conn.send('[helo]')
                while True:
                    data = conn.recv()
                    if not data:
                        break

                    logger.info(f'client say {data}')

                    if data == 'quit':
                        logger.info('quit')
                        conn.send('[bye]')
                        sys.exit(0)

                    elif data == 'pid':
                        logger.info(f'pid {pid}')
                        conn.send(f'{pid}')

                    else:
                        logger.info(f'server echo {data}')
                        conn.send(f'[{data}]')

                logger.info('client bye')
        except Exception as e:
            logger.info(e)

        logger.info('server bye')
