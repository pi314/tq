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
    NORMAL = 0
    BLOCK = 1
    QUEUE = 2

    def __init__(self, tid=None, cwd='', cmd='', args=[], block=NORMAL, cap_out=False):
        now = datetime.now()
        if tid:
            self.tid = tid
        else:
            self.tid = now.strftime('%Y%m%d_%H%M%S_') + '%06d'%(now.microsecond)

        self.cwd = cwd
        self.cmd = cmd
        self.args = list(args)
        self.block = block
        self.cap_out = cap_out

        self.lock = MyOneWayLock() if self.block == Task.BLOCK else None

        self.status = 'init'
        self.ret = None

    def copy(self):
        return Task(cwd=self.cwd, cmd=self.cmd, args=self.args, block=self.block, cap_out=self.cap_out)

    def to_dict(self):
        ret = {}
        ret['tid'] = self.tid
        ret['status'] = self.status
        ret['cwd'] = self.cwd
        ret['cmd'] = self.cmd
        ret['args'] = self.args
        ret['ret'] = self.ret
        return ret

    def __str__(self):
        s = []
        s.append('[{}] tid: {}'.format(self.status, self.tid))
        s.append('[{}] cwd: {}'.format(self.status, self.cwd))
        s.append('[{}] cmd: {}'.format(self.status, self.cmd))
        for i in self.args:
            s.append('[{}] arg: {}'.format(self.status, i))

        if self.ret is not None:
            s.append('[{}] ret: {}'.format(self.status, self.ret))

        return '\n'.join(s)


class MsgSubmitTask:
    def __init__(self, task):
        self.task = task


class MsgGeneralResult:
    def __init__(self, result, reason):
        self.result = result
        self.reason = reason


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
    def __init__(self, timeout):
        self.timeout = timeout


class MsgBlock:
    pass


class MsgUnblock:
    pass
