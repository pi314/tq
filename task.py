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
    def __init__(self, tid=None, cwd='', cmd='', args=[], block=False):
        now = datetime.now()
        if not tid:
            self.tid = now.strftime('%Y%m%d_%H%M%S_') + '%06d'%(now.microsecond)

        self.lock = None

        self.cwd = cwd
        self.cmd = cmd
        self.args = list(args)

        if block:
            self.lock = MyOneWayLock()

        self.status = 'init'
        self.ret = None

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
