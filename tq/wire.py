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


class TQSession(TQAddr):
    def __init__(self, pid, conn=None):
        super().__init__(pid)
        self.conn = conn

        if not self.conn:
            self.conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.conn.connect(self.addr)

        self.rw = self.conn.makefile('rw', encoding='utf8')

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
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
            except:
                pass

            try:
                self.rw.close()
            except:
                pass

            try:
                self.conn.close()
            except:
                pass
            self.conn = None

    def send(self, msg):
        try:
            self.rw.write(msg.serialize() + '\n')
            self.rw.flush()
        except:
            pass

    def recv(self):
        try:
            payload = ''
            payload = self.rw.readline()
            packet = json.loads(payload)
            txid = packet['txid']
            tipe = packet['tipe']
            tag = packet['tag']
            args = packet['args']
            if tipe == 'cmd':
                return TQCommand(txid, tag, args)
            elif tipe == 'res':
                return TQResult(txid, tag, args)
            elif tipe == 'evt':
                return TQEvent(txid, tag, args)
            raise ValueError(tipe)
        except:
            if not payload:
                return TQMessage(None, None, None, payload)


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
    def __init__(self, txid, tipe, tag, args):
        super().__setattr__('txid', txid)
        super().__setattr__('tipe', tipe)
        super().__setattr__('tag', tag)
        super().__setattr__('args', args)

    def __bool__(self):
        return bool(self.txid) or self.tipe != 'unknown' or bool(self.tag) or bool(self.args)

    def __repr__(self):
        return f'TQMessage(txid={self.txid}, tipe={self.tipe}, tag={self.tag})'

    def __getattr__(self, attr):
        if isinstance(self.args, dict):
            return self.args.get(attr)

    def serialize(self):
        import json
        return json.dumps({
            'txid': self.txid,
            'tipe': self.tipe,
            'tag': self.tag,
            'args': self.args,
            })


class TQCommand(TQMessage):
    def __init__(self, txid, cmd, args={}):
        super().__init__(txid, 'cmd', cmd, args)

    @property
    def cmd(self):
        return self.tag

    def __repr__(self):
        return f'TQCommand(txid={self.txid}, cmd={self.cmd})'


class TQResult(TQMessage):
    def __init__(self, txid, res, args={}):
        super().__init__(txid, 'res', res, args)

    @property
    def res(self):
        return self.tag

    def __repr__(self):
        return f'TQResult(txid={self.txid}, res={self.tag})'


class TQEvent(TQMessage):
    def __init__(self, txid, event, args={}):
        super().__init__(txid, 'evt', event, args)

    @property
    def event(self):
        return self.tag

    def __repr__(self):
        return f'TQEvent(txid={self.txid}, event={self.tag})'
