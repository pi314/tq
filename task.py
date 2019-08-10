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
    def __init__(self, *args):
        now = datetime.now()
        self.tid = now.strftime('%Y%m%d_%H%M%S_') + '%06d'%(now.microsecond)
        self.lock = None

        if isinstance(args[0], str):
            self.cwd = args[0]
            self.cmd = list(args[1])

        elif isinstance(args[0], dict):
            d = args[0]
            self.cwd = d['cwd']
            self.cmd = d['cmd']

            if 'block' in d and d['block']:
                self.lock = MyOneWayLock()

    def to_dict(self):
        ret = {}
        ret['tid'] = self.tid
        ret['cwd'] = self.cwd
        ret['cmd'] = self.cmd
        return ret
