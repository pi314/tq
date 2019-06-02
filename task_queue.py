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
task = None


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
            req = json.loads(self.readline())
        except json.decoder.JSONDecodeError:
            self.writeresult('400 Bad Request', 'Invalid format')
            return

        cmd = req.get('cmd', None)
        if not cmd:
            self.writeresult('400 Bad Request', 'Should provide cmd')
            return

        if cmd == 'dump':
            self.handle_dump()
        else:
            self.handle_cmd(req)

    def handle_dump(self):
        data = {}
        if task:
            data['working'] = {}
            data['working']['cwd'] = task.cwd
            data['working']['cmd'] = task.cmd
            data['working']['args'] = task.args

        data['pending'] = []
        while not task_queue.empty():
            t = task_queue.get()
            i = {}
            i['cwd'] = t.cwd
            i['cmd'] = t.cmd
            i['args'] = t.args
            data['pending'].append(i)

        self.writejson(data)

    def handle_cmd(self, req):
        cmd = req['cmd']
        cwd = req.get('cwd', None)
        if not cwd:
            self.writeresult('400 Bad Request', 'Should provide cwd')
            return

        args = req.get('args', None)
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


def send_req(req):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((HOST, PORT))

            def writeline(line):
                sock.sendall((line + '\n').encode('utf-8'))

            def writejson(obj):
                writeline(json.dumps(obj))

            writejson(req)

            sock.shutdown(socket.SHUT_WR)

            res = ''
            while True:
                data = sock.recv(1024).strip()
                if not data: break
                res += data.decode('utf-8')

            res = json.loads(res)
            print(json.dumps(res, indent=4))

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


# =============================================================================
# Public interface
# -----------------------------------------------------------------------------
def start():
    global task

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
    req = {}
    req['cwd'] = os.getcwd()
    req['cmd'] = cmd
    req['args'] = argv
    send_req(req)


def dump():
    req = {}
    req['cmd'] = 'dump'
    send_req(req)


def load():
    data = ''
    for line in sys.stdin:
        data += line.rstrip()

    try:
        data = json.loads(data)

        if 'working' in data:
            w = data['working']
            t = Task(w['cwd'], w['cmd'], w['args'])
            task_queue.put(t)

            for p in data['pending']:
                t = Task(p['cwd'], p['cmd'], p['args'])
                task_queue.put(t)

        start()

    except json.decoder.JSONDecodeError:
        log_error('Invalid JSON string')
        return 1

# -----------------------------------------------------------------------------
# Public interface
# =============================================================================
