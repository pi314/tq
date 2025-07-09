import os
import json

from . import server
from . import channel


_session = None


def detect():
    return server.detect()


def spawn():
    return server.spawn()


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
        return channel.TQServerCommandResult(401, 'Not connected')
    _session.close()


def bye():
    disconnect()


def echo(*args, **kwargs):
    if not _session:
        return channel.TQServerCommandResult(401, 'Not connected')

    _session.send(channel.TQServerCommand('echo', *args, **kwargs))
    return _session.recv()


def enqueue(cmd, cwd=None, env=None):
    if not cwd:
        cwd = os.getcwd()

    if not env:
        env = dict(os.environ)


def shutdown():
    if not _session:
        return channel.TQServerCommandResult(401, 'Not connected')

    _session.send(channel.TQServerCommand('despawn'))
    return _session.recv()
