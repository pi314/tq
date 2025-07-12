import os
import sys

import queue
import threading

import logging

from os.path import expanduser, exists

from . import daemon
from . import channel
from .config import TQ_DIR, TQ_LOG_FNAME

ss = None
bye = None

worker_mailbox = None
next_task_id = 1

task_finished_queue = []
task_ongoing = None
task_pending_queue = []


def spawn():
    daemon_pid = daemon.read_pid_file()
    if daemon_pid is not None and daemon_pid != os.getpid():
        return daemon_pid

    ret = daemon.spawn()
    if isinstance(ret, int) or ret is None:
        return ret

    onready = ret
    boot(onready)


def shutdown():
    bye.set()
    logging.info('shutdown()')
    ss.close()
    worker_mailbox.put(None)

    # import signal
    # os.kill(os.getpid(), signal.SIGINT)


def boot(onready):
    global bye
    global worker_mailbox

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
    worker_mailbox = queue.Queue()

    logging.info('start worker thread')
    t1 = threading.Thread(target=worker_thread, daemon=True)
    t1.start()

    logging.info('start frontdesk thread')
    t2 = threading.Thread(target=frontdesk_thread, args=(onready,), daemon=True)
    t2.start()

    try:
        t1.join()
        t2.join()
    except (Exception, SystemExit) as e:
        logging.exception(e)
    except KeyboardInterrupt as e:
        logging.info('KeyboardInterrupt')

    if ss:
        ss.close()

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
                if not conn:
                    continue

                logging.info('client connected')
                try:
                    handle_client(conn)
                except ModuleNotFoundError as e:
                    logging.exception(e)
                    shutdown()
                except BrokenPipeError as e:
                    logging.info('client BrokenPipeError')
                except (Exception, KeyboardInterrupt, SystemExit) as e:
                    logging.exception(e)
                conn.close()
                logging.info('client disconnected')

    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    logging.info('frontdesk thread bye')


def handle_client(conn):
    from .channel import TQResult
    global next_task_id

    while not bye.is_set():
        msg = conn.recv()
        if not msg:
            break

        result = handle_msg(conn, msg)
        if result is False:
            logging.info(f'server 400')
            conn.send(TQResult(400))
            break


def handle_msg(conn, msg):
    from .channel import TQResult

    logging.info(f'handle_msg(): {msg}')

    if msg.cmd == 'shutdown':
        shutdown()

    elif msg.cmd == 'echo':
        logging.info(f'server echo {msg.kwargs}')
        conn.send(TQResult(200, msg.kwargs))

    elif msg.cmd == 'enqueue':
        from .task import Task
        worker_mailbox.put(Task(next_task_id, **msg.kwargs))
        conn.send(TQResult(200, msg.kwargs))

    else:
        return False


def worker_thread():
    logging.info('worker thread start')

    try:
        while not bye.is_set():
            task = worker_mailbox.get()
            if not task:
                continue

            logging.info(task)

    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    logging.info('worker thread bye')
