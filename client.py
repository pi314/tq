import json
import os
import socket

from . import HOST, PORT

from .task import Task


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

            res = b''
            while True:
                data = sock.recv(1024)
                if not data: break
                res += data

            try:
                res = json.loads(res.decode('utf-8').strip())
            except json.decoder.JSONDecodeError:
                print('JSONDecodeError')

            try:
                sock.shutdown(socket.SHUT_RD)
            except OSError:
                pass

            try:
                sock.close()
            except OSError:
                pass

        return res

    except ConnectionRefusedError:
        return {'status': 400, 'reason': 'Task queue is not running'}

    return {'status': 400, 'reason': 'WTF'}


def submit_task(task):
    req = {}
    req['cwd'] = task.cwd
    req['cmd'] = task.cmd
    req['args'] = task.args
    req['block'] = task.block

    try:
        res = send_req(req)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        return 1

    if res['status'] < 200 or 300 <= res['status']:
        print(res)
        return 1

    if task.block != Task.BLOCK:
        print(res)
        return 0

    if task.cmd == 'd':
        return 0

    os.execvp(task.cmd, [task.cmd] + task.args)


def request_dump():
    req = {}
    req['cwd'] = os.getcwd()
    req['cmd'] = 'dump'
    req['args'] = []

    try:
        res = send_req(req)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        return 1

    if res and 200 <= res['status'] and res['status'] < 300:
        for idx, item in enumerate(res.get('data', [])):
            t = Task(tid=item['tid'], cwd=item['cwd'], cmd=item['cmd'], args=item['args'])
            t.status = item['status']
            print()
            print(idx)
            print(str(t))
    else:
        print(res)


def set_autoquit(autoquit):
    req = {}
    req['cwd'] = os.getcwd()
    req['cmd'] = 'autoquit' if autoquit else 'noautoquit'
    req['args'] = []

    try:
        res = send_req(req)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        return 1

    print(res)
