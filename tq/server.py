import os
import sys

import queue
import threading

import logging

from os.path import expanduser, exists

from . import daemon
from .config import TQ_DIR, TQ_LOG_FNAME
from .wire import TQCommand, TQResult, TQEvent
from .server_utils import TQServerSocket, ClientList, ServerEventHub
from .server_utils import TaskList, Task

ss = None

task_list = None
client_list = None
event_hub = None


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
    globals()['shutdown'] = lambda:None
    logging.info('shutdown()')
    try:
        task_list.quit()
    except:
        pass
    try:
        client_list.kick()
    except:
        pass
    try:
        ss.close()
    except:
        pass

    # import signal
    # os.kill(os.getpid(), signal.SIGINT)


def boot(onready):
    global task_list
    global client_list
    global event_hub

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

    task_list = TaskList()
    client_list = ClientList()
    event_hub = ServerEventHub()

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
            while True:
                conn = ss.accept()
                if not conn:
                    break

                t = threading.Thread(target=handle_client, args=(conn,), daemon=True)
                client_list.add(conn)
                t.start()

    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    try:
        if client_list:
            logging.info(f'Kick {len(client_list)} clients')
            client_list.kick()
    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    logging.info('frontdesk thread bye')
    shutdown()


class ClientLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        ppid = self.extra['ppid']
        return f'[ppid={ppid}] {msg}', kwargs


def handle_client(conn):
    logger = ClientLoggerAdapter(logging.getLogger(), {'ppid': conn.ppid})
    logger.info(f'client connected, {len(client_list)} online')
    try:
        while True:
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

    try:
        client_list.bye(conn)
        event_hub.remove(conn)
        logger.info(f'client disconnected, {len(client_list)} online')
    except (Exception, SystemExit) as e:
        logger.exception(e)
        shutdown()


def handle_msg(logger, conn, msg):
    logger.info(f'handle_msg(): txid={msg.txid} cmd={msg.cmd}')

    if msg.cmd == 'shutdown':
        shutdown()

    elif msg.cmd == 'echo':
        logger.info(f'server echo {msg.args}')
        conn.send(TQResult(msg.txid, 200, {'args': msg.args}))

    elif msg.cmd == 'enqueue':
        task_id = task_list.append(Task(**msg.args))
        conn.send(TQResult(msg.txid, 200, {'task_id': task_id}))

    elif msg.cmd == 'block':
        task_list.block()
        logger.info(f'task_list ttb={task_list.time_to_block}')
        conn.send(TQResult(msg.txid, 200))

    elif msg.cmd == 'unblock':
        task_list.unblock(count=msg.count)
        logger.info(f'task_list ttb={task_list.time_to_block}')
        conn.send(TQResult(msg.txid, 200))

    elif msg.cmd == 'wait':
        conn.send(TQResult(msg.txid, 501))

    elif msg.cmd == 'list':
        with task_list:
            for task in task_list.finished_list + [task_list.current] + task_list.pending_list:
                if task:
                    conn.send(TQResult(msg.txid, 100, task.info))
        conn.send(TQResult(msg.txid, 200))

    elif msg.cmd == 'subscribe':
        with task_list:
            with event_hub:
                res = event_hub.add(conn, msg.txid)
                conn.send(TQResult(msg.txid, 200 if res else 409))

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
        logging.info(f'task_list len={len(task_list)}')
        while task_list.wait():
            logging.info(f'task_list len={len(task_list)}')
            logging.info(f'task={task_list.current}')
            if task_list.current:
                task_info = task_list.current.info
                task_info['status'] = 'start'
                event_hub.broadcast('task', task_info)
                task_list.current.run()
                event_hub.broadcast('task', task_list.current.info)
                task_list.archive()
            logging.info(f'task_list len={len(task_list)}')

    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    logging.info('worker thread bye')
    shutdown()
