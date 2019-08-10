import json
import os
import socket

from . import HOST, PORT
from . import drive_cmd

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


def submit_task(cmd, args, block):
    req = {}
    req['cwd'] = os.getcwd()
    req['cmd'] = cmd
    req['args'] = args
    req['block'] = block

    try:
        res = send_req(req)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        return 1

    if not block:
        if cmd == 'dump':
            for i in res.get('data', []):
                t = Task(cwd=i['cwd'], cmd=i['cmd'], args=i['args'])
                t.status = i['status']
                print()
                print(str(t))
        else:
            print(res)
        return

    if res and 200 <= res['status'] and res['status'] < 300:
        if cmd == 'd':
            drive_cmd.run(args[0], args[1:])
        else:
            os.execvp(cmd, [cmd] + args)

    else:
        print(res)
        return 1
