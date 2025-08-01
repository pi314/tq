import subprocess as sub
import threading
import socket

from .config import TQ_DIR
from .wire import TQAddr, TQSession, TQEvent


class TQServerSocket:
    def __init__(self, pid):
        self.pid = pid
        self.addr = TQAddr(pid)
        self.ss = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def open(self):
        self.addr.file.unlink(missing_ok=True)
        self.ss = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.ss.bind(self.addr.addr)
        self.ss.listen()

    def close(self):
        try:
            self.ss.shutdown(socket.SHUT_RDWR)
        except:
            pass
        self.ss.close()
        self.addr.file.unlink(missing_ok=True)

    def accept(self):
        try:
            conn, addr = self.ss.accept()
            return TQSession(self.pid, conn)
        except:
            pass


class TaskQueue:
    def __init__(self):
        self.bye = False
        self.finished_list = []
        self.current = None
        self.pending_list = []
        self.index = {}

        self.next_id = 1
        self.rlock = threading.RLock()
        self.go = threading.Event()
        self.pass_num = None

    @property
    def time_to_block(self):
        with self:
            return self.pass_num

    def __enter__(self):
        self.rlock.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.rlock.release()

    def __iter__(self):
        with self:
            yield from self.finished_list
            if self.current:
                yield self.current
            yield from self.pending_list

    def __getitem__(self, index):
        with self:
            return self.index.get(index)

    def __bool__(self):
        return bool(self.pending_list)

    def __len__(self):
        return len(self.pending_list)

    def wait(self):
        self.go.wait()
        with self:
            if self.pending_list:
                self.current = self.pending_list.pop(0)

        return self.current is not None

    def quit(self):
        self.unblock()
        self.insert(None)

    def append(self, task):
        with self:
            return self.insert(task, index=None)

    def insert(self, task, index=0):
        with self:
            if task:
                task.setup(self.next_id)
                self.next_id += 1
                self.index[task.id] = task
            if index is None:
                self.pending_list.append(task)
            else:
                self.pending_list.insert(index, task)
            self.check_if_ok_to_go()
            return task.id if task else None

    def cancel(self, task_id):
        with self:
            task = self.index.get(task_id, None)
            if task:
                try:
                    self.pending_list.remove(task)
                    task.canceled = True
                    self.finished_list.append(task)
                except:
                    return False
            return True

    def clear(self, task_id):
        try:
            with self:
                task = self.index.get(task_id, None)
                if not task or task.status in ('pending', 'running'):
                    return False
                self.finished_list.remove(task)
                task.teardown()
                return True
        except:
            return False

    def archive(self):
        with self:
            self.finished_list.append(self.current)
            self.current = None
            if self.pass_num is not None:
                self.pass_num -= 1
            self.check_if_ok_to_go()

    def check_if_ok_to_go(self):
        if self.pending_list and self.pass_num != 0:
            self.go.set()
        else:
            self.go.clear()

    def block(self):
        with self:
            self.pass_num = 0
            self.check_if_ok_to_go()

    def unblock(self, count=None):
        with self:
            self.pass_num = count
            self.check_if_ok_to_go()

    def urgent(self, task_id):
        with self:
            task = self.index.get(task_id, None)
            if not task or task.status != 'pending':
                return False

            self.pending_list.remove(task)
            self.pending_list.insert(0, task)
            return True

    def move(self, task_id, drift):
        with self:
            task = self.index.get(task_id, None)
            if not task or task.status != 'pending':
                return False

            idx = self.pending_list.index(task)
            new_idx = min(max((idx + drift), 0), (len(self.pending_list) - 1))
            if new_idx != idx:
                l = self.pending_list
                l[idx], l[new_idx] = l[new_idx], l[idx]
                return True
            else:
                return False


class Task:
    def __init__(self, cmd, cwd=None, env=None):
        self.id = 0
        self.cmd = cmd
        self.cwd = cwd
        self.env = env
        self.canceled = False

        self.proc = None
        self.exception = None

    def __repr__(self):
        return f'Task(id={self.id}, cmd={self.cmd})'

    @property
    def info(self):
        ret = {
                'task_id': self.id,
                'pid': self.proc.pid if self.proc else None,
                'cmd': self.cmd,
                'cwd': self.cwd,
                'stdout': str(self.stdout_file),
                'stderr': str(self.stderr_file),
                'returncode': self.proc.returncode if self.proc else None,
                'status': self.status,
                }
        if self.error:
            ret['error'] = self.error
        return ret

    @property
    def cmd_file(self):
        if self.id:
            return TQ_DIR / f'tq.task.{self.id}.cmd'

    @property
    def stdout_file(self):
        if self.id:
            return TQ_DIR / f'tq.task.{self.id}.stdout'

    @property
    def stderr_file(self):
        if self.id:
            return TQ_DIR / f'tq.task.{self.id}.stderr'

    @property
    def ret_file(self):
        if self.id:
            return TQ_DIR / f'tq.task.{self.id}.returncode'

    @property
    def error(self):
        if self.exception:
            return str(self.exception)

    @property
    def status(self):
        if self.exception:
            return 'error'
        if self.canceled:
            return 'canceled'
        if not self.proc:
            return 'pending'
        if self.proc.returncode is None:
            return 'running'
        return 'finished'

    def setup(self, task_id):
        self.id = task_id

        TQ_DIR.mkdir(parents=True, exist_ok=True)
        self.cmd_file.touch(exist_ok=True)
        self.stdout_file.touch(exist_ok=True)
        self.stderr_file.touch(exist_ok=True)
        self.ret_file.touch(exist_ok=True)

        with open(self.cmd_file, 'w') as f:
            f.write(str(self.cmd) + '\n')

    def run(self):
        try:
            with open(self.stdout_file, 'wb') as stdout_file:
                with open(self.stderr_file, 'wb') as stderr_file:
                    self.proc = sub.Popen(self.cmd, cwd=self.cwd,
                                          stdout=stdout_file, stderr=stderr_file,
                                          env=self.env)
                    returncode = self.proc.wait()
                    if returncode < 0:
                        returncode = 128 - returncode
                    with open(self.ret_file, 'w') as ret_file:
                        ret_file.write(f'{returncode}\n')
        except (Exception, KeyboardInterrupt, SystemExit) as e:
            self.exception = e

    def kill(self, sig=None):
        if self.proc:
            import signal
            import os
            os.kill(self.proc.pid, sig or signal.SIGKILL)

    def teardown(self):
        for f in [self.cmd_file, self.stdout_file, self.stderr_file, self.ret_file]:
            try:
                f.unlink(missing_ok=True)
            except:
                pass


class ClientList:
    def __init__(self):
        self.clients = []
        self.rlock = threading.RLock()

    def __enter__(self):
        self.rlock.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.rlock.release()

    def __len__(self):
        return len(self.clients)

    def add(self, conn):
        with self:
            self.clients.append(conn)

    def kick(self, conn=None):
        with self:
            if conn is not None:
                self.bye(conn)

            else:
                for c in self.clients:
                    c.close()
                self.clients = []

    def bye(self, conn):
        try:
            with self:
                conn.close()
                self.clients.remove(conn)
        except:
            pass


class ServerEventHub:
    def __init__(self):
        self.subscribers = {}
        self.rlock = threading.RLock()

    def __enter__(self):
        self.rlock.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.rlock.release()

    def add(self, conn, txid):
        with self:
            if conn.ppid in self.subscribers:
                return False
            self.subscribers[conn.ppid] = (conn, txid)
            return True

    def remove(self, conn):
        with self:
            if conn.ppid not in self.subscribers:
                return False
            del self.subscribers[conn.ppid]
            return True

    def broadcast(self, event, args={}):
        with self:
            for conn, txid in self.subscribers.values():
                conn.send(TQEvent(txid, event, args))
