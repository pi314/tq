import atexit
import pathlib

from os.path import expanduser, exists

from .config import TQ_DIR, TQ_PID_FILE
from .core_server import serve


def read_pid_file():
    if not TQ_PID_FILE.exists():
        return
    try:
        with open(TQ_PID_FILE) as f:
            return int(f.read(), 10)
    except:
        return


def write_pid_file():
    TQ_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(TQ_PID_FILE, 'w') as f:
            import os
            f.write(f'{os.getpid()}\n')
    except:
        return


def del_pid_file():
    TQ_PID_FILE.unlink(missing_ok=True)
    TQ_DIR.unlink(missing_ok=True)


def spawn():
    import os
    import sys

    daemon_pid = read_pid_file()
    if daemon_pid is not None and daemon_pid != os.getpid():
        return daemon_pid

    try:
        r, w = os.pipe()
        pid = os.fork()
        if pid > 0:
            # exit first parent
            # readline() is necessary over read()
            try:
                return int(os.fdopen(r).readline().strip())
            except ValueError:
                return
    except OSError as e:
        sys.stderr.write(f'fork #1 failed: {e.errno} (e.strerror)\n')
        sys.exit(1)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f'fork #2 failed: {e.errno} (e.strerror)\n')
        sys.exit(1)

    write_pid_file()

    # read pid file back to make sure it's me
    daemon_pid = read_pid_file()
    if daemon_pid is not None and daemon_pid != os.getpid():
        os.write(w, f'{daemon_pid}\n'.encode('utf8'))
        sys.exit(1)

    atexit.register(del_pid_file)

    # newline is necessary
    os.write(w, f'{daemon_pid}\n'.encode('utf8'))

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'w')
    se = open(os.devnull, 'w')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    serve()
