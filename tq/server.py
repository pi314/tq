import os
import sys

import threading

import logging

from os.path import expanduser, exists

from . import daemon
from .config import TQ_DIR, TQ_LOG_FNAME
from .wire import TQCommand, TQResult, TQEvent
from .server_utils import TQServerSocket, ClientList, ServerEventHub
from .server_utils import TaskQueue, Task

ss = None

task_queue = None
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
        logging.info('task_queue.quit()')
        task_queue.quit()
    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    try:
        logging.info('client_list.kick()')
        client_list.kick()
    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    try:
        logging.info('ss.close()')
        ss.close()
    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    # import signal
    # os.kill(os.getpid(), signal.SIGINT)


def boot(onready):
    global task_queue
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

    task_queue = TaskQueue()
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
            elif result is True:
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
    logger.info(f'handle_msg(): txid={msg.txid}, cmd={msg.cmd}, args={msg.args if msg.cmd != "enqueue" else "{...}"}')

    if msg.cmd == 'shutdown':
        shutdown()
        return True

    elif msg.cmd == 'echo':
        conn.send(TQResult(msg.txid, 200, {'args': msg.args}))

    elif msg.cmd == 'enqueue':
        task_id = task_queue.append(Task(**msg.args.ref))
        conn.send(TQResult(msg.txid, 200, {'task_id': task_id}))

    elif msg.cmd == 'block':
        task_queue.block()
        logger.info(f'task_queue ttb={task_queue.time_to_block}')
        conn.send(TQResult(msg.txid, 200))

    elif msg.cmd == 'unblock':
        task_queue.unblock(count=msg.args.count)
        logger.info(f'task_queue ttb={task_queue.time_to_block}')
        conn.send(TQResult(msg.txid, 200))

    elif msg.cmd == 'wait':
        conn.send(TQResult(msg.txid, 501))

    elif msg.cmd == 'list':
        query_list = msg.args.task_id_list
        try:
            ret = []
            with task_queue:
                if not msg.task_id_list:
                    # Query without task_id_list
                    for task in task_queue:
                        ret.append(task.info)
                else:
                    # Query with task_id_list
                    for task_id in msg.args.task_id_list:
                        task = task_queue[task_id]
                        if task:
                            ret.append(task.info)
                        else:
                            ret.append({'task_id': task_id, 'error': 'unknown task id'})
            conn.send(TQResult(msg.txid, 200, ret))
        except:
            conn.send(TQResult(msg.txid, 500))

    elif msg.cmd == 'subscribe':
        with task_queue, event_hub:
            res = event_hub.add(conn, msg.txid)
            conn.send(TQResult(msg.txid, 200 if res else 409))

            if msg.args.finished:
                for task in task_queue:
                    if task.status in ('finished', 'error'):
                        conn.send(TQEvent(msg.txid, 'task', task.info))

            if task_queue.current:
                conn.send(TQEvent(msg.txid, 'task', task_queue.current.info))

    elif msg.cmd == 'cancel':
        with task_queue:
            ret = []
            for task_id in msg.args.task_id_list:
                if task_queue[task_id] is None:
                    res = 404
                elif task_queue[task_id].status != 'pending':
                    res = 409
                elif task_queue.cancel(task_id):
                    res = 200
                else:
                    res = 500
                ret.append({'task_id': task_id, 'result': res})
            conn.send(TQResult(msg.txid, 200, ret))

    else:
        return False


def worker_thread():
    logging.info('worker thread start')

    try:
        logging.info(f'task_queue len={len(task_queue)}')
        while task_queue.wait():
            logging.info(f'task_queue len={len(task_queue)}')
            logging.info(f'task={task_queue.current}')
            if task_queue.current:
                task_info = task_queue.current.info
                task_info['status'] = 'start'
                event_hub.broadcast('task', task_info)
                task_queue.current.run()
                event_hub.broadcast('task', task_queue.current.info)
                task_queue.archive()
            logging.info(f'task_queue len={len(task_queue)}')

    except (Exception, KeyboardInterrupt, SystemExit) as e:
        logging.exception(e)

    logging.info('worker thread bye')
    shutdown()
