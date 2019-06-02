import json
import os
import socket
import socketserver
import sys

from queue import Queue
from threading import Thread

from . import HOST, PORT

from .worker import do_job
from .utils import log_error


task_queue = Queue()


class Task:
    def __init__(self, cwd, cmd, args):
        self.cwd = cwd
        self.cmd = cmd
        self.args = args


class MyTCPHandler(socketserver.StreamRequestHandler):
    def readline(self):
        return self.rfile.readline().strip().decode('utf-8')

    def writeline(self, line):
        self.wfile.write((line + '\n').encode('utf-8'))

    def writejson(self, obj):
        self.writeline(json.dumps(obj))

    def writeresult(self, status, reason):
        res = {}
        res['status'] = status
        res['reason'] = reason
        self.writejson(res)

    def handle(self):
        try:
            data = json.loads(self.readline())
        except json.decoder.JSONDecodeError:
            self.writeresult('400 Bad Request', 'Invalid format')
            return

        cwd = data.get('cwd', None)
        if not cwd:
            self.writeresult('400 Bad Request', 'Should provide cwd')
            return

        cmd = data.get('cmd', None)
        if not cmd:
            self.writeresult('400 Bad Request', 'Should provide cmd')
            return

        args = data.get('args', None)
        if not args:
            self.writeresult('400 Bad Request', 'No arguments provided')
            return

        task_queue.put(Task(cwd, cmd, args))

        self.writeresult('202 Accepted', '')


def server_frontend():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
        server.serve_forever()


def print_task_status(task, status):
    print('_______________________________________________________________________________')
    print('['+ status +'] cwd:', task.cwd)
    print('['+ status +'] cmd:', task.cmd)
    for i in task.args:
        print('['+ status +'] arg:', i)
    print('⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻⎻')


def start():
    t = Thread(target=server_frontend)
    t.daemon = True
    t.start()

    try:
        while True:
            task = task_queue.get()
            os.chdir(task.cwd)
            print_task_status(task, 'working')
            do_job(task.cmd, task.args)
            print_task_status(task, 'finish')

    except KeyboardInterrupt:
        log_error('KeyboardInterrupt')
        while not task_queue.empty():
            task = task_queue.get()
            print_task_status(task, 'canceled')

    return 1


def add_task(cmd, argv):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((HOST, PORT))

            def writeline(line):
                sock.sendall((line + '\n').encode('utf-8'))

            def writejson(obj):
                writeline(json.dumps(obj))

            data = {}
            data['cwd'] = os.getcwd()
            data['cmd'] = cmd
            data['args'] = argv
            writejson(data)

            sock.shutdown(socket.SHUT_WR)

            while True:
                data = sock.recv(1024).strip()
                if not data: break
                print(data.decode('utf-8'))

            try:
                sock.shutdown(socket.SHUT_RD)
            except OSError:
                pass

            try:
                sock.close()
            except OSError:
                pass

    except ConnectionRefusedError:
        print('Task queue not running')
