import json
import socket

from . import HOST, PORT

from .models import *


def serialize(msg):
    if isinstance(msg, MsgSubmitTaskList):
        obj = {}
        obj['msg'] = 'MsgSubmitTaskList'
        obj['task_list'] = []
        for task in msg.task_list:
            obj['task_list'].append({
                    'tid': task.tid,
                    'cwd': task.cwd,
                    'cmd': task.cmd,
                    'args': task.args,
                    'block': task.block,
                })
        return json.dumps(obj)

    if isinstance(msg, MsgGeneralResult):
        return json.dumps({'msg': 'MsgGeneralResult', 'result': msg.result, 'reason': msg.reason})

    if isinstance(msg, MsgUnblockTask):
        return json.dumps({'msg': 'MsgUnblockTask', 'tid': msg.tid})

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
                'block': t.block,
                'status': t.status,
                })
        return json.dumps(obj)

    if isinstance(msg, MsgQuitNext):
        return json.dumps({'msg': 'MsgQuitNext'})

    if isinstance(msg, MsgSetAutoQuit):
        return json.dumps({'msg': 'MsgSetAutoQuit', 'timeout': msg.timeout})

    if isinstance(msg, MsgCurrAutoQuit):
        return json.dumps({'msg': 'MsgCurrAutoQuit', 'config': msg.config, 'remain': msg.remain})

    raise Exception('Cannot serialize ' + repr(msg))


def deserialize(msg):
    try:
        msg = json.loads(msg)
    except json.decoder.JSONDecodeError:
        return MsgGeneralResult(400, 'JSONDecodeError')

    if 'msg' not in msg:
        return MsgGeneralResult(400, 'Incorrect format')

    if msg['msg'] == 'MsgSubmitTaskList':
        task_list = []
        for task_item in msg['task_list']:
            task_list.append(Task(
                task_item['tid'],
                task_item['cwd'],
                task_item['cmd'],
                task_item['args'],
                task_item['block'],
                ))
        return MsgSubmitTaskList(task_list)

    if msg['msg'] == 'MsgGeneralResult':
        return MsgGeneralResult(msg['result'], msg['reason'])

    if msg['msg'] == 'MsgUnblockTask':
        return MsgUnblockTask(msg['tid'])

    if msg['msg'] == 'MsgGetTaskList':
        return MsgGetTaskList()

    if msg['msg'] == 'MsgTaskList':
        task_list = []
        for task_item in msg['task_list']:
            task = Task(
                    task_item['tid'],
                    task_item['cwd'],
                    task_item['cmd'],
                    task_item['args'],
                    task_item['block'],
                    )
            task.status = task_item['status']
            task_list.append(task)
        return MsgTaskList(task_list)

    if msg['msg'] == 'MsgQuitNext':
        return MsgQuitNext()

    if msg['msg'] == 'MsgSetAutoQuit':
        return MsgSetAutoQuit(msg['timeout'])

    if msg['msg'] == 'MsgCurrAutoQuit':
        return MsgCurrAutoQuit(msg['config'], msg['remain'])

    raise Exception('Cannot deserialize ' + repr(msg))
