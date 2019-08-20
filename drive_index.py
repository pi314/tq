import argparse
import re
import subprocess as sub

from os import getcwd
from os import walk
from os.path import join
from threading import Thread
from unicodedata import east_asian_width

from .logger import log_error
from .utils import get_drive_root, run


dindex_local = 'dindex.local'
dindex_remote = 'dindex.remote'


TTY_COLS = 0


def str_width(s):
    return sum(1 + (east_asian_width(c) in 'WF') for c in s)


def print_nowrap(s, **kwargs):
    if not TTY_COLS:
        print(s, **kwargs)
        return

    buf = ''
    buf_w = 0
    for i in s:
        w = str_width(i)
        if buf_w + w >= TTY_COLS:
            break

        buf += i
        buf_w += w

    print('\r' + buf + (' ' * (TTY_COLS - buf_w)) + '\r', **kwargs)


def writeline(f, line):
    f.write((line.rstrip() + '\n').encode('utf-8'))


def ignore_fname(driveignore, fname):
    for p in driveignore:
        if p.match(fname):
            return True

    return False


def index_local(params):
    count = 0
    plist = []
    for root, subdirs, files in walk(params.cwd):
        for f in files:
            if ignore_fname(params.driveignore, f):
                continue

            if f.startswith('.'):
                continue

            depth_cwd = len(params.cwd.split('/'))
            depth_root = len(root.split('/'))

            line = (join(root, f)[len(params.cwd)+1:])
            plist.append(line)

            count += 1
            print_nowrap('[local ] {count}: {line}'.format(count=count, line=line), end='')

        if params.depth != 0:
            depth_cwd = len(params.cwd.split('/'))
            depth_root = len(root.split('/'))
            if depth_root - depth_cwd >= params.depth - 1:
                del subdirs[:]

        removee = list(filter(lambda x: x.startswith('.'), subdirs))
        for r in removee:
            subdirs.remove(r)

    print_nowrap('[local ] {count} items indexed'.format(count=len(plist)))

    with open(dindex_local, 'wb') as f:
        for p in sorted(plist):
            writeline(f, p)


def index_remote(params):
    cmd = 'drive list -files -recursive -no-prompt'.split()
    if params.depth != 0:
        cmd.remove('-recursive')
        cmd += ['-depth', str(params.depth)]

    p = sub.Popen(cmd, stdout=sub.PIPE)

    plist = []
    count = 0
    for line in iter(p.stdout.readline, b''):
        line = line.decode('utf-8').rstrip('\n')
        if not line: continue

        if line.startswith('/'):
            line = line[1:]

        count += 1
        print_nowrap('[remote] {count}: {line}'.format(count=count, line=line), end='')

        if params.cwd == params.root:
            plist.append(line[line.index('/')+1:])
        else:
            plist.append(join(params.root, line)[len(params.cwd)+1:])

    print_nowrap('[remote] {count} items indexed'.format(count=len(plist)))

    with open(dindex_remote, 'wb') as f:
        for p in sorted(plist):
            writeline(f, p)


def main(argv):
    global TTY_COLS

    p = run(['stty', 'size'], capture_output=True)

    TTY_COLS = int(p.stdout.split()[1], 10)

    parser = argparse.ArgumentParser(prog='dindex',
            description='d sub-command - index')

    parser.add_argument('-depth', default=0, type=int,
            help='index depth')

    parser.add_argument('target',
            nargs='?',
            choices=('all', 'local', 'remote'),
            default='all',
            help='index local, remote or both')

    parser.set_defaults(local=False, remote=False)

    params = parser.parse_args(argv)

    if params.target == 'all':
        params.local = True
        params.remote = True

    elif params.target == 'local':
        params.local = True

    elif params.target == 'remote':
        params.remote = True

    params.cwd = getcwd()
    params.root = get_drive_root()
    params.driveignore = []

    if not params.root:
        log_error('Drive context not found')
        return 1

    with open(join(params.root, '.driveignore')) as f:
        for line in f:
            line = line.rstrip('\n')
            params.driveignore.append(re.compile(line))

    try:
        if params.local:
            index_local(params)

        if params.remote:
            index_remote(params)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        return 1

    print('[local ] index file:', dindex_local)
    print('[remote] index file:', dindex_remote)
