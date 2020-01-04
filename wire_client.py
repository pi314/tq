import json
import os
import socket

from . import HOST, PORT

from .models import *
from .lib_wire import *
from .lib_utils import *


def send_cmds(*cmd_list):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((HOST, PORT))

            for cmd in cmd_list:
                sock.sendall((serialize(cmd) + '\n').encode('utf-8'))

            sock.shutdown(socket.SHUT_WR)

            buf = b''
            while True:
                data = sock.recv(1024)
                if not data: break
                buf += data

            if not buf:
                return [MsgGeneralResult(500, 'Empty content')]

            lines = buf.decode('utf-8').strip().split('\n')

            res_list = [deserialize(line) for line in lines]

            try:
                sock.shutdown(socket.SHUT_RD)
            except OSError:
                pass

            try:
                sock.close()
            except OSError:
                pass

        return res_list

    except ConnectionRefusedError:
        return [MsgGeneralResult(400, 'Task queue is not running')]

    return [MsgGeneralResult(400, 'WTF')]


def submit_task(task):
    try:
        res_list = send_cmds(MsgSubmitTaskList([task]))
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        return 1

    res = res_list[0]
    if res.result < 200 or 300 <= res.result:
        print(res)
        return 1

    if task.block != Task.BLOCK:
        print(res)
        return 0

    if task.cmd == 'd':
        return 0

    os.execvp(task.cmd, [task.cmd] + task.args)


def get_task_list():
    res_list = send_cmds(MsgGetTaskList())

    for res in res_list:
        if isinstance(res, MsgTaskList):
            for idx, task in enumerate(res.task_list):
                print()
                print(idx)
                print(task)
        else:
            print(res)


def set_auto_quit(timeout):
    res_list = send_cmds(MsgSetAutoQuit(timeout))

    for res in res_list:
        print(res)
