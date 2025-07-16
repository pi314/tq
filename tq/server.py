import os
import sys

import queue
import threading

import logging

from os.path import expanduser, exists

from . import daemon
from .wire import TQServerSocket, TQCommand, TQResult, TQEvent
from .config import TQ_DIR, TQ_LOG_FNAME

ss = None
bye = None

next_task_id = 1

task_list = None

client_lock = threading.Lock()
client_list = []


def detect():
    return daemon.detect()


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
    task_list.quit()

    # import signal
    # os.kill(os.getpid(), signal.SIGINT)


def boot(onready):
    global bye
    global task_list

    from logging.handlers import RotatingFileHandler
    one_mb = 1024 * 1024
    logging.basicConfig(
            handlers=[RotatingFileHandler(
                filename=f'{TQ_DIR / TQ_LOG_FNAME}', maxBytes=one_mb, backupCount=5
                )],
            level=logging.INFO,
            datefmt='%Y-%m-%d %H:%M:%S',
            format=f'[%(asctime)s.%(msecs)03d][{os.getpid()}] %(message)s')

    logging.info('=' * 40)

    bye = threading.Event()

    from .task import TaskList
    task_list = TaskList()

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
        logging.info('boot(): KeyboardInterrupt')

    if ss:
        ss.close()

    logging.info('server quit')
    logging.info('=' * 40)
    sys.exit(0)


def frontdesk_thread(onready):
    global ss

    logging.info('frontdesk thread start')
    ss = TQServerSocket(os.getpid())
    try:
        with ss:
            onready(os.getpid())
            while not bye.is_set():
                conn = ss.accept()
                if not conn:
                    continue

                t = threading.Thread(target=handle_client, args=(conn,), daemon=True)
                with client_lock:
                    client_list.append((t, conn))
                t.start()

    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    try:
        logging.info(f'Kick {len(client_list)} clients')
        for t, conn in client_list:
            conn.close()
            t.join()

    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    logging.info('frontdesk thread bye')


class ClientLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        ppid = self.extra['ppid']
        return f'[ppid={ppid}] {msg}', kwargs


def handle_client(conn):
    logger = ClientLoggerAdapter(logging.getLogger(), {'ppid': conn.ppid})
    logger.info(f'client connected, {len(client_list)} online')
    try:
        while not bye.is_set():
            msg = conn.recv()
            if not msg:
                break

            result = handle_msg(logger, conn, msg)
            if result is False:
                logger.info('server 400')
                conn.send(TQResult(msg.txid, 400))
                break
    except ModuleNotFoundError as e:
        logger.exception(e)
        shutdown()
    except BrokenPipeError as e:
        logger.info('client BrokenPipeError')
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt')
    except (Exception, SystemExit) as e:
        logger.exception(e)
    conn.close()

    try:
        with client_lock:
            for idx, (t, client_conn) in enumerate(client_list):
                if client_conn is conn:
                    client_list.pop(idx)
                    break
    except (Exception, SystemExit) as e:
        logger.exception(e)
    logger.info(f'client disconnected, {len(client_list)} online')


def handle_msg(logger, conn, msg):
    global next_task_id

    logger.info(f'handle_msg(): txid={msg.txid} cmd={msg.cmd}')

    if msg.cmd == 'shutdown':
        shutdown()

    elif msg.cmd == 'echo':
        logger.info(f'server echo {msg.args}')
        conn.send(TQResult(msg.txid, 200, {'args': msg.args}))

    elif msg.cmd == 'enqueue':
        from .task import Task
        task_id = task_list.append(Task(**msg.args))
        conn.send(TQResult(msg.txid, 200, {'task_id': task_id}))

    elif msg.cmd == 'list':
        with task_list:
            for task in task_list.finished + [task_list.current] + task_list.pending:
                if task:
                    info = {
                            'task_id': task.id,
                            'cmd': task.cmd,
                            'status': task.status,
                            }
                    if task.status == 'error':
                        info['error'] = task.error
                    conn.send(TQResult(msg.txid, 100, info))
        conn.send(TQResult(msg.txid, 200))

    elif msg.cmd == 'cancel':
        with task_list:
            task = task_list.remove(msg.args['task_id'])
            if task:
                conn.send(TQResult(msg.txid, 200, {'task_id': task.id}))
            else:
                conn.send(TQResult(msg.txid, 404, {'task_id': msg.args['task_id']}))

    else:
        return False


def worker_thread():
    logging.info('worker thread start')

    try:
        while not bye.is_set():
            logging.info(f'task_list len={len(task_list)}')
            task_list.wait()
            if bye.is_set():
                break

            logging.info(task_list.current)
            if task_list.current:
                task_list.current.run()
                task_list.archive()

    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    logging.info('worker thread bye')
