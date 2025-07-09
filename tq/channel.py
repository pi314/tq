import socket
import json


class TQAddr:
    def __init__(self, pid):
        self.pid = pid

    @property
    def file(self):
        from .config import TQ_DIR, TQ_SOCKET_FILE_PREFIX
        return TQ_DIR / f'{TQ_SOCKET_FILE_PREFIX}{self.pid}'

    @property
    def addr(self):
        return str(self.file).encode('utf8')


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
        except OSError:
            pass
        self.ss.close()
        self.addr.file.unlink(missing_ok=True)

    def accept(self):
        try:
            conn, addr = self.ss.accept()
            return TQSession(self.pid, conn)
        except ConnectionAbortedError:
            pass


class TQSession(TQAddr):
    def __init__(self, pid, conn=None):
        super().__init__(pid)
        self.conn = conn

        if not self.conn:
            self.conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.conn.connect(self.addr)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def alive(self):
        if self.conn is None:
            return False

        try:
            self.conn.recv(16, socket.MSG_DONTWAIT | socket.MSG_PEEK)
        except BlockingIOError:
            return True
        except ConnectionResetError:
            return False

        return True

    def __bool__(self):
        return self.alive

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def send(self, cmd):
        self.conn.sendall(cmd.serialize())

    def recv(self):
        raw_data = b''
        while True:
            payload = self.conn.recv(1024)
            raw_data += payload

            try:
                data = json.loads(raw_data.decode('utf8'))
            except ValueError:
                if not payload:
                    return TQRawMessage(raw_data)
                continue

            cmd = data.get('cmd')
            status = data.get('status')
            args = data.get('args')
            kwargs = data.get('kwargs')
            msg_type = TQServerCommand if cmd else TQServerCommandResult
            return msg_type(cmd or status, *args, **kwargs)


class TQNotSession:
    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def __bool__(self):
        return False


class TQRawMessage:
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return f'TQRawMessage({self.data})'

    def __bool__(self):
        return not not self.data


class TQServerCommand:
    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        self.args = args
        self.kwargs = kwargs

    def serialize(self):
        return json.dumps({
            'cmd': self.cmd,
            'args': self.args,
            'kwargs': self.kwargs,
            }).encode('utf8')


class TQServerCommandResult:
    def __init__(self, status, *args, **kwargs):
        self.status = status
        self.args = args
        self.kwargs = kwargs

    def serialize(self):
        return json.dumps({
            'status': self.status,
            'args': self.args,
            'kwargs': self.kwargs,
            }).encode('utf8')
