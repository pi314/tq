import json
import os
import socket
import socketserver
import subprocess as sub

from datetime import datetime
from queue import Queue
from threading import Thread

from . import HOST, PORT
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
            t = Task(req)
            if t.lock:
                log_task_status(t, 'blocking')
                telegram.notify_task(t, 'blocking')
                task_queue.put(t)
            else:
                log_task_status(t, 'pending')
                # telegram.notify_task(t, 'pending')
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

            if not current_task.lock:
                log_task_status(current_task, 'working')
                telegram.notify_task(current_task, 'working')

            if current_task.cmd[0] == 'quit':
                log_task_status(current_task, 'done')
                telegram.notify_task(current_task, 'done')

            elif current_task.lock:
                current_task.lock.notify()
                log_task_status(current_task, 'unblocked')
                telegram.notify_task(current_task, 'unblocked')

            else:
                os.chdir(current_task.cwd)
                p = sub.run(current_task.cmd)
                log_task_status(current_task, 'done', p.returncode)
                telegram.notify_task(current_task, 'done')

            if current_task.cmd[0] == 'quit':
                break

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
