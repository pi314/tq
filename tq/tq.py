import os
import json

from . import daemon
from . import server
from . import channel


_session = None


msg_not_connected = channel.TQResult(401, msg='Not connected')


def detect():
    return daemon.detect()


def spawn():
    return server.spawn()


def shutdown():
    if not _session:
        return msg_not_connected

    _session.send(channel.TQCommand('shutdown'))
    return _session.recv()


def connect(spawn=True):
    global _session

    server_pid = detect()

    if not server_pid and spawn:
        server_pid = globals().get('spawn')()
        server_pid = detect()

    if server_pid:
        _session = channel.TQSession(server_pid)
    else:
        _session = channel.TQNotSession()

    return _session


def disconnect():
    if not _session:
        return msg_not_connected
    _session.close()


def bye():
    disconnect()


def echo(**kwargs):
    if not _session:
        return msg_not_connected

    _session.send(channel.TQCommand('echo', **kwargs))
    return _session.recv()


def enqueue(cmd, cwd=None, env=None):
    if not cwd:
        cwd = os.getcwd()

    if not env:
        env = dict(os.environ)
