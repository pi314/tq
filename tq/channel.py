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

    def send(self, msg):
        self.conn.sendall(msg.serialize())

    def recv(self):
        raw_data = b''
        while True:
            payload = self.conn.recv(1024)
            raw_data += payload

            try:
                return TQMessage(json.loads(raw_data.decode('utf8')))
            except ValueError:
                if not payload:
                    return TQMessage(raw_data)
                else:
                    continue


class TQNotSession:
    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def __bool__(self):
        return False


class TQMessage:
    def __init__(self, data):
        super().__setattr__('data', data)

    def __bool__(self):
        return bool(self.data)

    def __repr__(self):
        return f'TQMessage(data={self.data})'

    def __getattr__(self, attr):
        if isinstance(self.data, dict):
            return self.data.get(attr)

    def serialize(self):
        import json
        return json.dumps(self.data).encode('utf8')


class TQCommand(TQMessage):
    def __init__(self, cmd, kwargs={}):
        super().__init__({
            'cmd': cmd,
            'kwargs': kwargs,
            })


class TQResult(TQMessage):
    def __init__(self, res, kwargs={}):
        super().__init__({
            'res': res,
            'kwargs': kwargs,
            })
