import json

from . import core_server
from . import core_channel


def spawn():
    return core_server.spawn()


def connect(spawn=True, pid=None):
    if pid is None:
        pid = core_server.detect()

    if not pid and spawn:
        pid = core_server.spawn()

    pid = core_server.detect()
    if pid:
        return core_channel.create_client_socket(pid)
