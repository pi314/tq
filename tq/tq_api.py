import os
import json
import threading
import itertools

from . import daemon
from . import server
from .wire import TQSession, TQNotSession, TQCommand, TQResult, TQEvent


msg_not_connected = TQResult(None, 401, {'msg': 'Not connected'})


session = None

_txid = itertools.count(1)
def txid():
    return next(_txid)


def detect():
    return daemon.detect()


def spawn():
    return server.spawn()


def shutdown():
    if not session:
        return msg_not_connected

    session.send(TQCommand(txid(), 'shutdown'))
    return session.recv()


def connect(spawn=True):
    global session

    server_pid = detect()

    if not server_pid and spawn:
        server_pid = globals().get('spawn')()
        server_pid = detect()

    if server_pid:
        session = TQSession(server_pid)
    else:
        session = TQNotSession()

    return session


def disconnect():
    if not session:
        return msg_not_connected
    session.close()


def bye():
    disconnect()


def echo(**kwargs):
    if not session:
        return msg_not_connected

    session.send(TQCommand(txid(), 'echo', kwargs))
    return session.recv()


def enqueue(cmd, cwd=None, env=None):
    if not session:
        return msg_not_connected

    if not cwd:
        cwd = os.getcwd()

    if not env:
        env = dict(os.environ)

    session.send(TQCommand(txid(), 'enqueue', {
        'cmd': cmd,
        'cwd': cwd,
        'env': env,
        }))
    return session.recv()


def list():
    session.send(TQCommand(txid(), 'list'))
    while True:
        msg = session.recv()
        if msg:
            yield msg

        if not msg or msg.res >= 200:
            break


def cancel(task_id):
    session.send(TQCommand(txid(), 'cancel', {
        'task_id': int(task_id)
        }))
    return session.recv()
