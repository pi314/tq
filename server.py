import json
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
from . import config
from . import drive_cmd
from . import telegram

from .task import Task
from .logger import log_create, log_task_status, log_dict, log_info, log_error


task_queue = Queue()
current_task = None
quitnext = None
auto_quit = True


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
        global quitnext
        global auto_quit

        try:
            req = json.loads(''.join(self.readlines()))
        except json.decoder.JSONDecodeError:
            self.writeresult(400, 'JSONDecodeError')
            return

        if req['cmd'] == 'dump':
            self.handle_dump()
            return

        if req['cmd'] == 'quitnext':
            quitnext = Task(cwd=req['cwd'], cmd=req['cmd'], args=req['args'], block=req.get('block', None))
            quitnext.status = 'pending'
            log_task_status(quitnext)
            self.writeresult(202, 'Accepted')
            return

        if req['cmd'] == 'autoquit':
            if not req['args']:
                self.writejson({'autoquit': auto_quit})
                return

            m = re.match(r'^(\d+)([msh])$', req['args'][0])
            if not m:
                self.writejson({'autoquit': auto_quit})
                return

            time = int(m.group(1)) * {'s': 1, 'm': 60, 'h': 3600}[m.group(2)]

            auto_quit = time
            self.writejson({'autoquit': auto_quit})
            return

        t = Task(cwd=req['cwd'], cmd=req['cmd'], args=req['args'], block=req.get('block', None))
        if t.lock:
            t.status = 'blocking'
            log_task_status(t)
            task_queue.put(t)
        else:
            t.status = 'pending'
            log_task_status(t)
            task_queue.put(t)

        if t.lock:
            t.lock.wait()
            self.writeresult(200, 'OK')

        else:
            self.writeresult(202, 'Accepted')

    def handle_dump(self):
        res = {}
        res['status'] = 200
        res['reason'] = 'OK'

        data = []

        if current_task:
            data.append(current_task.to_dict())

        if quitnext:
            data.append(quitnext.to_dict())

        for t in list(task_queue.queue):
            data.append(t.to_dict())

        res['data'] = data

        self.writejson(res)


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

    t = Thread(target=server.serve_forever)
    t.daemon = True
    t.start()

    t2 = Thread(target=telegram.loop_start)
    t2.daemon = True
    t2.start()

    ret = 0

    log_create()

    print(sys.version_info)
    print('[status] start')
    # telegram.notify_msg('[status] start')
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d_%H:%M:%S_') + '%06d'%(now.microsecond)
    log_dict({'status': 'start', 'time': timestamp})

    try:
        while True:
            if quitnext:
                quitnext.status = 'succeed'
                log_task_status(quitnext)
                telegram.notify_task(quitnext)
                break

            current_task = task_queue.get()

            if current_task.cmd in ('quit', 'quitnext'):
                current_task.status = 'succeed'
                log_task_status(current_task)
                telegram.notify_task(current_task)
                break

            if current_task.lock:
                current_task.lock.notify()
                current_task.status = 'unblocked'
                log_task_status(current_task)
                telegram.notify_task(current_task)

            else:
                current_task.status = 'working'
                log_task_status(current_task)
                telegram.notify_task(current_task)

                os.chdir(current_task.cwd)
                if current_task.cmd == 'd':
                    ret = drive_cmd.run(current_task)
                    log_task_status(current_task)
                    if current_task.status == 'interrupted':
                        raise KeyboardInterrupt

                else:
                    try:
                        p = sub.run([current_task.cmd] + current_task.args)
                        current_task.status = 'failed' if p.returncode else 'succeed'
                        current_task.ret = p.returncode
                    except FileNotFoundError:
                        current_task.status = 'error'

                    log_task_status(current_task)
                    telegram.notify_task(current_task)

            current_task = None

            if task_queue.empty():
                print()
                print('[status] empty')
                log_dict({'status': 'empty'})
                telegram.notify_msg('[status] empty')
                if auto_quit:
                    now = datetime.now()
                    timestamp = now.strftime('%Y%m%d_%H:%M:%S_') + '%06d'%(now.microsecond)
                    log_dict({'status': 'stop', 'reason': 'auto_quit', 'time': timestamp})
                    telegram.notify_msg('[status] stop (auto_quit)')
                    break

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


def load(dry):
    global quitnext
    global task_queue

    acc_log = {}

    fname = config.get('log', 'filename')
    if not exists(fname):
        return start()

    with open(fname) as f:
        for line in f:
            try:
                log_entry = json.loads(line)
            except json.decoder.JSONDecodeError:
                pass

            if 'tid' in log_entry and 'status' in log_entry:
                acc_log[log_entry['tid']] = log_entry

    acc_log = dict(filter(lambda x: x[1]['status'] not in ('failed', 'succeed', 'blocking', 'unblocked'), acc_log.items()))

    for tid in sorted(acc_log):
        e = acc_log[tid]
        t = Task(tid=e['tid'], cwd=e['cwd'], cmd=e['cmd'], args=e['args'])
        t.status = 'pending'

        if t.cmd == 'quitnext':
            quitnext = t

        else:
            task_queue.put(t)

    if quitnext:
        tq_buf = Queue()
        if not task_queue.empty():
            tq_buf.put(task_queue.get())

        tq_buf.put(quitnext)
        quitnext = None

        while not task_queue.empty():
            tq_buf.put(task_queue.get())

        task_queue = tq_buf

    if dry:
        while not task_queue.empty():
            t = task_queue.get()
            print()
            print(t)

        return

    return start()
