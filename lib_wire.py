import json
import socket

from .models import *


def serialize(msg):
    if isinstance(msg, MsgSubmitTask):
        obj = {}
        obj['msg'] = 'MsgSubmitTask'
        obj['task'] = {}
        obj['task']['cwd'] = task.cwd
        obj['task']['cmd'] = task.cmd
        obj['task']['args'] = task.args
        obj['task']['block'] = task.block
        return json.dumps(obj)

    if isinstance(msg, MsgGeneralResult):
        return json.dumps({'msg': 'MsgGeneralResult', 'result': msg.result, 'reason': msg.reason})

    if isinstance(msg, MsgGetTaskList):
        return json.dumps({'msg': 'MsgGetTaskList'})

    if isinstance(msg, MsgTaskList):
        obj = {}
        obj['msg'] = 'MsgTaskList'
        obj['task_list'] = []
        for t in msg.task_list:
            obj['task_list'].append({
                'tid': t.tid,
                'cwd': t.cwd,
                'cmd': t.cmd,
                'args': t.args,
                'status': t.status,
                })
        return json.dumps(obj)

    if isinstance(msg, MsgQuitNext):
        return json.dumps({'msg': 'MsgQuitNext'})

    if isinstance(msg, MsgSetAutoQuit):
        return json.dumps({'msg': 'MsgSetAutoQuit', 'timeout': msg.timeout})

    if isinstance(msg, MsgCurrAutoQuit):
        return json.dumps({'msg': 'MsgCurrAutoQuit', 'timeout': msg.timeout})

    if isinstance(msg, MsgBlock):
        return json.dumps({'msg': 'MsgBlock'})

    if isinstance(msg, MsgUnblock):
        return json.dumps({'msg': 'MsgUnblock'})

    raise Exception('Cannot serialize ' + repr(msg))


def deserialize(msg):
    msg = json.loads(msg)

    if msg['msg'] == 'MsgSubmitTask':
        raise Exception('Not implemented yet')

    if msg['msg'] == 'MsgGeneralResult':
        return MsgGeneralResult(msg['result'], msg['reason'])

    if msg['msg'] == 'MsgGetTaskList':
        return MsgGetTaskList()

    if msg['msg'] == 'MsgTaskList':
        raise Exception('Not implemented yet')

    if msg['msg'] == 'MsgQuitNext':
        return MsgQuitNext()

    if msg['msg'] == 'MsgSetAutoQuit':
        return MsgSetAutoQuit(msg['timeout'])

    if msg['msg'] == 'MsgCurrAutoQuit':
        return MsgCurrAutoQuit(msg['timeout'])

    if msg['msg'] == 'MsgBlock':
        return MsgBlock()

    if msg['msg'] == 'MsgUnblock':
        return MsgUnblock()

    raise Exception('Cannot deserialize ' + repr(msg))


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

            lines = buf.decode('utf-8').strip().split('\n')

            try:
                res_list = [deserialize(line for line in lines)]
            except json.decoder.JSONDecodeError:
                return MsgGeneralResult(500, 'JSONDecodeError')

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
        return MsgGeneralResult(400, 'Task queue is not running')

    return MsgGeneralResult(400, 'WTF')
