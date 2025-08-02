import subprocess as sub
import threading
import socket
import json

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
    def post(handler):
        def decorator(f):
            def wrapper(self, *args, **kwargs):
                ret = f(self, *args, **kwargs)
                handler(self)
                return ret
            return wrapper
        return decorator

    def lock(f):
        def wrapper(self, *args, **kwargs):
            with self:
                return f(self, *args, **kwargs)
        return wrapper

    def __init__(self):
        self.bye = threading.Event()
        self.finished_list = []
        self._current = None
        self.pending_list = []
        self.index = {}

        self.next_id = 1
        self.rlock = threading.RLock()
        self.go = threading.Event()
        self.pass_num = None

    @property
    def queue_file(self):
        return TQ_DIR / f'tq.queue'

    @property
    def time_to_block(self):
        with self:
            return self.pass_num

    @property
    def current(self):
        if self._current is not None:
            return self[self._current]

    def __enter__(self):
        self.rlock.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.rlock.release()

    def __iter__(self):
        with self:
            for task_id in self.finished_list:
                yield self[task_id]
            if self.current:
                yield self.current
            for task_id in self.pending_list:
                yield self[task_id]

    def __getitem__(self, index):
        with self:
            return self.index.get(index)

    def __bool__(self):
        return bool(self.pending_list)

    def __len__(self):
        return len(self.pending_list)

    def update_queue_file(self):
        with open(self.queue_file, 'w') as f:
            obj = {
                    'finished': self.finished_list,
                    'running': self._current,
                    'pending': self.pending_list,
                    }
            json.dump(obj, f, indent=4)

    def check_if_ok_to_go(self):
        if self.bye.is_set():
            self.go.set()
        elif self.pending_list and self.pass_num != 0:
            self.go.set()
        else:
            self.go.clear()

    def wait(self):
        self.go.wait()
        with self:
            if self.bye.is_set():
                return False

            if self.pending_list:
                self._current = self.pending_list.pop(0)

        return self.current is not None

    @post(check_if_ok_to_go)
    def quit(self):
        if self.current:
            self.current.kill()
        self.bye.set()
        self.unblock()

    @lock
    def append(self, task):
        return self.insert(task, index=None)

    @lock
    @post(check_if_ok_to_go)
    @post(update_queue_file)
    def insert(self, task, index=0):
        task.setup(self.next_id)
        self.next_id += 1
        self.index[task.id] = task
        if index is None:
            self.pending_list.append(task.id)
        else:
            self.pending_list.insert(index, task.id)
        return task.id if task else None

    @lock
    @post(check_if_ok_to_go)
    @post(update_queue_file)
    def cancel(self, task_id):
        if task_id in self.index:
            self[task_id].cancel()
        return True

    @lock
    @post(check_if_ok_to_go)
    @post(update_queue_file)
    def clear(self, task_id):
        try:
            task = self[task_id]
            if not task or task.status in ('pending', 'running'):
                return False
            self.finished_list.remove(task_id)
            task.teardown()
            return True
        except:
            return False

    @lock
    @post(check_if_ok_to_go)
    @post(update_queue_file)
    def archive(self):
        self.finished_list.append(self._current)
        self._current = None
        if self.pass_num is not None:
            self.pass_num -= 1

    @lock
    @post(check_if_ok_to_go)
    def block(self):
        self.pass_num = 0

    @lock
    @post(check_if_ok_to_go)
    def unblock(self, count=None):
        self.pass_num = count

    @lock
    @post(check_if_ok_to_go)
    @post(update_queue_file)
    def urgent(self, task_id):
        task = self[task_id]
        if not task or task.status != 'pending':
            return False

        self.pending_list.remove(task_id)
        self.pending_list.insert(0, task_id)
        return True

    @lock
    @post(check_if_ok_to_go)
    @post(update_queue_file)
    def move(self, task_id, drift):
        task = self[task_id]
        if not task or task.status != 'pending':
            return False

        idx = self.pending_list.index(task_id)
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
                'env': self.env,
                'stdout': str(self.stdout_file),
                'stderr': str(self.stderr_file),
                'returncode': self.proc.returncode if self.proc else None,
                'status': self.status,
                }
        if self.error:
            ret['error'] = self.error
        return ret

    @property
    def info_file(self):
        if self.id:
            return TQ_DIR / f'tq.task.{self.id}.info'

    @property
    def stdout_file(self):
        if self.id:
            return TQ_DIR / f'tq.task.{self.id}.stdout'

    @property
    def stderr_file(self):
        if self.id:
            return TQ_DIR / f'tq.task.{self.id}.stderr'

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
        self.stdout_file.touch(exist_ok=True)
        self.stderr_file.touch(exist_ok=True)

        self.update_info_file()

    def update_info_file(self):
        try:
            with open(self.info_file, 'w') as f:
                json.dump(self.info, f, indent=4)
        except:
            pass

    def cancel(self):
        self.canceled = True
        self.update_info_file()

    def run(self):
        if self.canceled:
            return
        try:
            from contextlib import ExitStack
            with ExitStack() as stack:
                stdout_file = stack.enter_context(open(self.stdout_file, 'wb'))
                stderr_file = stack.enter_context(open(self.stderr_file, 'wb'))
                self.proc = sub.Popen(self.cmd, cwd=self.cwd,
                                      stdout=stdout_file, stderr=stderr_file,
                                      env=self.env)
                self.update_info_file()
                returncode = self.proc.wait()
                if returncode < 0:
                    returncode = 128 - returncode
        except (Exception, KeyboardInterrupt, SystemExit) as e:
            self.exception = e
        finally:
            self.update_info_file()

    def kill(self, sig=None):
        if self.proc:
            import signal
            import os
            os.kill(self.proc.pid, sig or signal.SIGKILL)

    def teardown(self):
        for f in [self.info_file, self.stdout_file, self.stderr_file]:
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
