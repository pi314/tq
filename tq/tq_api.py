import os
import sys
import json
import threading
import itertools
import queue

from . import server
from .wire import TQSession, TQSessionnt, TQMessage, TQCommand, TQResult, TQEvent


msg_not_connected = TQResult(None, 401, {'msg': 'Not connected'})

def ignore_any_exceptions(func):
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (Exception, KeyboardInterrupt, SystemExit) as e:
            pass
    return wrapped


class SessionManager:
    def __init__(self):
        self.connection = None
        self.tx = {}
        self.txid = itertools.count(1)
        self.thread = None

    @property
    def pid(self):
        if self.connection:
            return self.connection.pid

    def __bool__(self):
        return bool(self.connection)

    def bye(self, txid):
        if txid in self.tx:
            del self.tx[txid]

    def bind(self, connection):
        self.connection = connection
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()

    def close(self):
        for tx in self.tx.values():
            tx.put(TQMessage(None, None, None, b''))
        if self.connection:
            self.connection.close()
        self.connection = None

    def worker(self):
        try:
            while self.connection:
                msg = self.connection.recv()
                if msg.txid in self.tx:
                    self.tx[msg.txid].put(msg)
        except (Exception, KeyboardInterrupt, SystemExit) as e:
            pass
        self.close()

    def send(self, msg):
        self.connection.send(msg)

    def recv(self, txid):
        return self.tx[txid].recv()

    def get(self):
        ret = Session(self, next(self.txid))
        self.tx[ret.txid] = ret
        return ret


class Session:
    def __init__(self, sm, txid):
        self.sm = sm
        self.txid = txid
        self.queue = queue.Queue()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.sm.bye(self.txid)
        self.sm = None
        self.queue = None

    def __bool__(self):
        return bool(self.sm)

    @ignore_any_exceptions
    def send(self, cls, *args, **kwargs):
        msg = cls(self.txid, *args, **kwargs)
        self.sm.send(msg)

    @ignore_any_exceptions
    def recv(self):
        return self.get()

    @ignore_any_exceptions
    def put(self, msg):
        self.queue.put(msg)

    @ignore_any_exceptions
    def get(self):
        return self.queue.get()


sm = SessionManager()


def detect():
    return server.detect()


def spawn():
    import subprocess as sub
    import inspect
    from os.path import dirname, abspath
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    module_path = dirname(dirname(abspath(filename)))
    env = os.environ
    env['PYTHONPATH'] = module_path
    p = sub.run([sys.executable, '-m', 'tq', '--daemon'],
                capture_output=True,
                encoding='utf8', text=True, env=env)
    try:
        return int(p.stdout.strip(), 10)
    except:
        return None


def shutdown():
    if not sm:
        return msg_not_connected

    with sm.get() as session:
        session.send(TQCommand, 'shutdown')
        return session.recv()


def connect(spawn=True):
    if sm:
        sm.close()

    server_pid = detect()

    if not server_pid and spawn:
        server_pid = globals().get('spawn')()
        server_pid = detect()

    if server_pid:
        sm.bind(TQSession(server_pid))
    else:
        sm.bind(TQSessionnt())

    return sm


def disconnect():
    if not sm:
        return msg_not_connected
    sm.close()


def bye():
    disconnect()


def echo(**kwargs):
    if not sm:
        return msg_not_connected

    with sm.get() as session:
        session.send(TQCommand, 'echo', kwargs)
        return session.recv()


def enqueue(cmd, cwd=None, env=None):
    if not sm:
        return msg_not_connected

    if not cwd:
        cwd = os.getcwd()

    if not env:
        env = dict(os.environ)

    with sm.get() as session:
        session.send(TQCommand, 'enqueue', {
            'cmd': cmd,
            'cwd': cwd,
            'env': env,
            })
        return session.recv()


def list(task_id_list=[]):
    with sm.get() as session:
        args = {'task_id_list': task_id_list} if task_id_list else {}
        session.send(TQCommand, 'list', args)
        return session.recv()


def block():
    with sm.get() as session:
        session.send(TQCommand, 'block')
        return session.recv()


def unblock(count=None):
    with sm.get() as session:
        session.send(TQCommand, 'unblock', {'count': count})
        return session.recv()


def urgent(task_id):
    with sm.get() as session:
        session.send(TQCommand, 'urgent', {'task_id': task_id})
        return session.recv()


def up(task_id):
    with sm.get() as session:
        session.send(TQCommand, 'up', {'task_id': task_id})
        return session.recv()


def down(task_id):
    with sm.get() as session:
        session.send(TQCommand, 'down', {'task_id': task_id})
        return session.recv()


def subscribe(callback, finished=False):
    def handler():
        try:
            with sm.get() as session:
                session.send(TQCommand, 'subscribe', args={'finished': finished})
                msg = session.recv()
                if not msg or msg.res < 200:
                    return

                while session:
                    msg = session.recv()
                    if callback(msg) == False or not msg:
                        break
        finally:
            callback(None)

    t = threading.Thread(target=handler, daemon=True)
    t.start()
    return t


def cancel(task_id_list):
    with sm.get() as session:
        args = {'task_id_list': task_id_list} if task_id_list else {}
        session.send(TQCommand, 'cancel', args)
        return session.recv()


def kill(task_id_list, signal=None):
    with sm.get() as session:
        args = {}
        if task_id_list:
            args['task_id_list'] = task_id_list
        if signal:
            args['signal'] = signal
        session.send(TQCommand, 'kill', args)
        return session.recv()


def clear(task_id_list):
    with sm.get() as session:
        args = {'task_id_list': task_id_list} if task_id_list else {}
        session.send(TQCommand, 'clear', args)
        return session.recv()


def retry(task_id_list):
    with sm.get() as session:
        args = {'task_id_list': task_id_list} if task_id_list else {}
        session.send(TQCommand, 'retry', args)
        return session.recv()
