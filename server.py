import json
import os
import socket
import socketserver
import subprocess as sub

from datetime import datetime
from queue import Queue
from threading import Thread

from . import HOST, PORT
from . import drive_cmd
from . import telegram

from .task import Task
from .logger import log_create, log_task_status, log_dict, log_info


task_queue = Queue()


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

    def writejson(self, obj):
        self.writeline(json.dumps(obj))

    def writeresult(self, status, reason):
        res = {}
        res['status'] = status
        res['reason'] = reason
        self.writejson(res)

    def handle(self):
        try:
            req = json.loads(''.join(self.readlines()))
            t = Task(cwd=req['cwd'], cmd=req['cmd'], args=req['args'], block=req.get('block', None))
            if t.lock:
                t.status = 'blocking'
                log_task_status(t)
                telegram.notify_task(t)
                task_queue.put(t)
            else:
                t.status = 'pending'
                log_task_status(t)
                task_queue.put(t)

        except json.decoder.JSONDecodeError:
            self.writeresult(400, 'JSONDecodeError')
            return

        if t.lock:
            t.lock.wait()
            self.writeresult(200, 'OK')

        else:
            self.writeresult(202, 'Accepted')


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def server_frontend():
    socketserver.TCPServer.allow_reuse_address = True
    with ThreadedTCPServer((HOST, PORT), MyTCPHandler) as server:
        server.serve_forever()


def start():
    socketserver.TCPServer.allow_reuse_address = True
    server = ThreadedTCPServer((HOST, PORT), MyTCPHandler)
    t = Thread(target=server.serve_forever)
    t.daemon = True
    t.start()

    t2 = Thread(target=telegram.loop_start)
    t2.daemon = True
    t2.start()

    ret = 0

    log_create()

    print('[status] start')
    # telegram.notify_msg('[status] start')
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d_%H:%M:%S_') + '%06d'%(now.microsecond)
    log_dict({'status': 'start', 'time': timestamp})

    try:
        while True:
            current_task = task_queue.get()

            if current_task.cmd == 'quit':
                current_task.status = 'succeed'
                log_task_status(current_task)
                telegram.notify_task(current_task)
                break

            if current_task.lock:
                current_task.lock.notify()
                current_task.status = 'unblocked'
                log_task_status(current_task)
                telegram.notify_task(current_task)
                continue

            current_task.status = 'working'
            log_task_status(current_task)
            telegram.notify_task(current_task)

            os.chdir(current_task.cwd)
            if current_task.cmd == 'd':
                drive_cmd.run(current_task.args[0], current_task.args[1:])
            else:
                p = sub.run([current_task.cmd] + current_task.args)
                current_task.status = 'failed' if p.returncode else 'succeed'
                current_task.ret = p.returncode
                log_task_status(current_task)
                telegram.notify_task(current_task)

            current_task = None

            if task_queue.empty():
                print()
                print('[status] empty')
                log_dict({'status': 'empty'})
                telegram.notify_msg('[status] empty')

    except KeyboardInterrupt:
        print()
        print('[status] stop: KeyboardInterrupt')
        now = datetime.now()
        timestamp = now.strftime('%Y%m%d_%H:%M:%S_') + '%06d'%(now.microsecond)
        log_dict({'status': 'stop', 'reason': 'KeyboardInterrupt', 'time': timestamp})
        # telegram.notify_msg('[status] stop: KeyboardInterrupt')
        ret = 1

    telegram.loop_stop()

    t2.join()

    return ret
