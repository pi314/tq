import os
import json

from . import daemon
from . import server
from .channel import TQSession, TQNotSession, TQCommand, TQResult


session = None


msg_not_connected = TQResult(401, {'msg': 'Not connected'})


def detect():
    return daemon.detect()


def spawn():
    return server.spawn()


def shutdown():
    if not session:
        return msg_not_connected

    session.send(TQCommand('shutdown'))
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

    session.send(TQCommand('echo', kwargs))
    return session.recv()


def enqueue(cmd, cwd=None, env=None):
    if not session:
        return msg_not_connected

    if not cwd:
        cwd = os.getcwd()

    if not env:
        env = dict(os.environ)

    session.send(TQCommand('enqueue', {
        'cmd': cmd,
        'cwd': cwd,
        'env': env,
        }))
    return session.recv()


def list():
    session.send(TQCommand('list'))
    while True:
        msg = session.recv()
        if msg:
            yield msg

        if not msg or msg.res >= 200:
            break


def cancel(task_id):
    session.send(TQCommand('cancel', {'task_id': int(task_id)}))
    return session.recv()
