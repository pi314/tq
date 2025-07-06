import atexit
import pathlib

from os.path import expanduser, exists

TQ_PID_FNAME = '.tq.pid'


def read_pid_file():
    pid_file = pathlib.Path.home() / TQ_PID_FNAME

    if not pid_file.exists():
        return

    try:
        with open(pid_file) as f:
            return int(f.read(), 10)
    except:
        return


def write_pid_file():
    pid_file = pathlib.Path.home() / TQ_PID_FNAME

    try:
        with open(pid_file, 'w') as f:
            import os
            f.write(f'{os.getpid()}\n')
    except:
        return


def del_pid_file():
    pid_file = pathlib.Path.home() / TQ_PID_FNAME
    pid_file.unlink(missing_ok=True)


def spawn(daemon_main):
    import os
    import sys

    daemon_pid = read_pid_file()
    if daemon_pid is not None and daemon_pid != os.getpid():
        sys.stderr.write(f'Already running {daemon_pid}\n')
        sys.exit(1)

    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
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
        sys.stderr.write(f'self pid {os.getpid()} != daemon pid {daemon_pid}')
        sys.exit(1)

    atexit.register(del_pid_file)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'w')
    se = open(os.devnull, 'w')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    daemon_main()
