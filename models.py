from datetime import datetime
from queue import Queue


class MyOneWayLock:
    def __init__(self):
        self.q = Queue()

    def wait(self):
        self.q.get()

    def notify(self):
        self.q.put(0)


class Task:
    LOCAL = 0
    BLOCK = 1
    QUEUE = 2

    @classmethod
    def gen_tid(cls):
        now = datetime.now()
        return now.strftime('%Y%m%d_%H%M%S_') + '%06d'%(now.microsecond)

    def __init__(self, tid, cwd, cmd, args, block, cap_out=False):
        self.tid = tid
        self.cwd = cwd
        self.cmd = cmd
        self.args = list(args)
        self.block = block
        self.cap_out = cap_out

        self.status = 'init'
        self.ret = None

        self.lock = MyOneWayLock() if self.block == Task.BLOCK else None

    def copy(self):
        tid = Task.gen_tid()
        return Task(tid=tid, cwd=self.cwd, cmd=self.cmd, args=self.args, block=self.block, cap_out=self.cap_out)

    def __repr__(self):
        return '<Task: [{}] {}>'.format(self.status, self.cmd)

    def __str__(self):
        prefix = '[' + self.status + ']'
        ret = [
            'tid: ' + self.tid,
            'cwd: ' + self.cwd,
            'cmd: ' + self.cmd,
        ] + [
            'arg: ' + arg for arg in self.args
        ] + [
            'blk: ' + str(self.block),
        ]

        return '\n'.join(map(lambda x: prefix + ' ' + x, ret))


class MsgSubmitTaskList:
    def __init__(self, task_list):
        self.task_list = task_list


class MsgGeneralResult:
    def __init__(self, result, reason):
        self.result = result
        self.reason = reason

    def __repr__(self):
        return '<MsgGeneralResult: {}, {}>'.format(self.result, self.reason)


class MsgUnblockTask:
    def __init__(self, tid):
        self.tid = tid


class MsgGetTaskList:
    pass


class MsgTaskList:
    def __init__(self, task_list):
        self.task_list = task_list


class MsgQuitNext:
    pass


class MsgSetAutoQuit:
    def __init__(self, timeout):
        self.timeout = timeout


class MsgCurrAutoQuit:
    def __init__(self, config, remain):
        self.config = config
        self.remain = remain

    def __repr__(self):
        return '<MsgCurrAutoQuit: config={}, remain={}>'.format(
                self.config, self.remain)
