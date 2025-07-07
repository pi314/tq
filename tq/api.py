import json

from . import core_server
from . import core_channel


def connect(spawn=True, pid=None):
    if pid is None:
        from .core_server import read_pid_file
        pid = read_pid_file()

    if not pid and spawn:
        pid = core_server.spawn()

    pid = read_pid_file()
    print(pid)
    if pid:
        return core_channel.create_client_socket(pid)
