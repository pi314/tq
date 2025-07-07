import socket


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
        conn, addr = self.ss.accept()
        return TQConnection(self.pid, conn)


class TQConnection(TQAddr):
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

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def recv(self):
        return self.conn.recv(1024).decode('utf8')

    def send(self, data):
        self.conn.sendall(data.encode('utf8'))


def create_server_socket(pid):
    return TQServerSocket(pid)


def create_client_socket(pid):
    return TQConnection(pid)
