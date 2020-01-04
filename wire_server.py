import os
import re
import socket
import socketserver
import subprocess as sub
import sys

from datetime import datetime
from queue import Queue
from threading import Thread
from os.path import exists

from . import HOST, PORT
from . import lib_config
from . import lib_drive_cmd
from . import lib_telegram
from . import task_queue

from .models import *
from .lib_logger import *
from .lib_wire import serialize, deserialize


class MyTCPHandler(socketserver.StreamRequestHandler):
    def readline(self):
        return self.rfile.readline().strip().decode('utf-8')

    def readlines(self):
        ret = []
        for line in self.rfile:
            ret.append(line.rstrip().decode('utf-8'))

        return ret

    def writeline(self, line=''):
        self.wfile.write((line.rstrip() + '\n').encode('utf-8'))

    def writeresult(self, status, reason):
        res = {}
        res['status'] = status
        res['reason'] = reason
        print(res)

    def handle(self):
        lines = self.readlines()
        for line in lines:
            msg = deserialize(line)

            if isinstance(msg, MsgSubmitTaskList):
                task_queue.submit_task_list(msg.task_list)
                self.writeline(serialize(MsgGeneralResult(202, 'Accepted')))

                for task in msg.task_list:
                    if task.lock:
                        task.lock.wait()
                        self.writeline(serialize(MsgUnblockTask(task.tid)))

                return

            if isinstance(msg, MsgGetTaskList):
                task_list = task_queue.get_task_list()
                self.writeline(serialize(MsgTaskList(task_list)))
                self.writeline(serialize(MsgGeneralResult(200, 'OK')))
                return

            if isinstance(msg, MsgQuitNext):
                self.writeline(serialize(MsgGeneralResult(501, 'Not Implemented')))
                return

            if isinstance(msg, MsgSetAutoQuit):
                task_queue.set_auto_quit(msg.timeout)
                self.writeline(serialize(MsgCurrAutoQuit(*task_queue.get_auto_quit())))
                return

            self.writeline(serialize(MsgGeneralResult(501, 'Not Implemented')))


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def start():
    global current_task

    socketserver.TCPServer.allow_reuse_address = True
    try:
        server = ThreadedTCPServer((HOST, PORT), MyTCPHandler)
    except OSError as e:
        if e.errno == 48:
            log_error(e)
            return 1

        raise e

    server.serve_forever()
    return
