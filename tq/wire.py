import socket
import json
import threading


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


class TQSession(TQAddr):
    def __init__(self, pid, conn=None):
        super().__init__(pid)
        self.conn = conn
        if not self.conn:
            self.conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.conn.connect(self.addr)

        self.wlock = threading.RLock()
        self.rw = self.conn.makefile('rw', encoding='utf8')
        self.ppid = self.conn.getsockopt(0, 2)

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
            return True
        except BlockingIOError:
            return True
        except:
            self.close()
            return False

    def __bool__(self):
        return self.alive

    def close(self):
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
        self.rw = None
        self.wlock = None

    def send(self, msg):
        try:
            with self.wlock:
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
                self.close()
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

    def close(self):
        pass


class TQJsonEncoder(json.JSONEncoder):
    def default(self, o):
        ret = o
        if isinstance(ret, AttrProxy):
            ret = ret.ref
        if isinstance(ret, (set, frozenset)):
            return list(ret)
        if ret is not o:
            return ret
        return super().default(o)


class AttrProxy:
    def __init__(self, ref=None):
        super().__setattr__('ref', {} if ref is None else ref)

    def __repr__(self):
        return f'{type(self).__name__}({repr(self.ref)})'

    def __bool__(self):
        return bool(self.ref)

    def __len__(self):
        return len(self.ref)

    def __iter__(self):
        for item in self.ref:
            if isinstance(item, (dict, list, tuple)):
                yield type(self)(item)
            else:
                yield item

    def __getattr__(self, attr):
        if hasattr(self.ref, attr):
            return getattr(self.ref, attr)
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value

    def __getitem__(self, index):
        if isinstance(self.ref, dict):
            ret = self.ref.get(index)
        else:
            try:
                ret = self.ref[index]
            except IndexError:
                return None
        if isinstance(ret, (dict, list, tuple)):
            return type(self)(ret)
        return ret

    def __setitem__(self, index, value):
        if isinstance(self.ref, list) and index == len(self):
            self.append(value)
        else:
            self.ref[index] = value


class TQMessage:
    def __init__(self, txid, tipe, tag, args):
        super().__setattr__('txid', txid)
        super().__setattr__('tipe', tipe)
        super().__setattr__('tag', tag)
        super().__setattr__('args', AttrProxy(args))

    def __bool__(self):
        return bool(self.txid) or bool(self.tipe) or bool(self.tag) or bool(self.args)

    def __repr__(self):
        return f'TQMessage(txid={self.txid}, tipe={self.tipe}, tag={self.tag}, args={self.args})'

    def __getattr__(self, attr):
        if isinstance(self.args, dict):
            return self.args.get(attr)

    def serialize(self):
        return json.dumps({
            'txid': self.txid,
            'tipe': self.tipe,
            'tag': self.tag,
            'args': self.args,
            }, cls=TQJsonEncoder)


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
