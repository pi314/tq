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


def submit_task(args):
    req = {}
    req['cwd'] = os.getcwd()
    if args.dump:
        req['cmd'] = 'dump'
        req['args'] = []
    else:
        req['cmd'] = args.cmd[0]
        req['args'] = args.cmd[1:]

    req['block'] = args.block

    try:
        res = send_req(req)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        return 1

    if not args.block:
        if args.dump:
            for i in res.get('data', []):
                t = Task(tid=i['tid'], cwd=i['cwd'], cmd=i['cmd'], args=i['args'])
                t.status = i['status']
                print()
                print(str(t))
        else:
            print(res)
        return

    if res and 200 <= res['status'] and res['status'] < 300:
        if args.cmd[0] == 'd':
            return 0
        else:
            os.execvp(args.cmd[0], args.cmd)

    else:
        print(res)
        return 1
