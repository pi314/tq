import re
import subprocess as sub

from os import getcwd
from os import walk
from os.path import join
from threading import Thread
from argparse import Namespace

from .utils import get_drive_root
from .utils import log_error


dindex_local = 'dindex.local'
dindex_remote = 'dindex.remote'


def writeline(f, line):
    f.write((line.rstrip() + '\n').encode('utf-8'))


def ignore_fname(driveignore, fname):
    for p in driveignore:
        if p.match(fname):
            return True

    return False


def index_local(params):
    print('Indexing local files ...')

    plist = []
    for root, subdirs, files in walk(params.cwd):
        for f in files:
            if ignore_fname(params.driveignore, f):
                continue

            if f.startswith('.'):
                continue

            depth_cwd = len(params.cwd.split('/'))
            depth_root = len(root.split('/'))

            plist.append(join(root, f)[len(params.cwd)+1:])

        if params.depth != 0:
            depth_cwd = len(params.cwd.split('/'))
            depth_root = len(root.split('/'))
            if depth_root - depth_cwd >= params.depth - 1:
                del subdirs[:]

        removee = list(filter(lambda x: x.startswith('.'), subdirs))
        for r in removee:
            subdirs.remove(r)

    with open(dindex_local, 'wb') as f:
        for p in sorted(plist):
            writeline(f, p)

    print('Indexing local files ... Done')


def index_remote(params):
    print('Indexing remote files ...')

    cmd = 'drive list -files -recursive -no-prompt'.split()
    if params.depth != 0:
        cmd.remove('-recursive')
        cmd += ['-depth', str(params.depth)]

    p = sub.Popen(cmd, stdout=sub.PIPE)

    plist = []
    for line in iter(p.stdout.readline, b''):
        line = line.decode('utf-8').rstrip('\n')
        if not line: continue

        if line.startswith('/'):
            line = line[1:]

        if params.cwd == params.root:
            plist.append(line[line.index('/')+1:])
        else:
            plist.append(join(params.root, line)[len(params.cwd)+1:])

    with open(dindex_remote, 'wb') as f:
        for p in sorted(plist):
            writeline(f, p)

    print('Indexing remote files ... Done')


def build_index(argv):
    params = Namespace()
    params.all = True
    params.local = False
    params.remote = False
    params.depth = 0

    while len(argv):
        arg = argv.pop(0)
        if arg == 'local':
            params.all = False
            params.local = True

        elif arg == 'remote':
            params.all = False
            params.remote = True

        elif arg == '-depth':
            params.depth = int(argv.pop(0))

        else:
            log_error('Unknown argument:', arg)

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

    t_local = None
    t_remote = None

    if params.all or params.local:
        t_local = Thread(target=index_local, args=(params,))
        t_local.daemon = True
        t_local.start()

    if params.all or params.remote:
        t_remote = Thread(target=index_remote, args=(params,))
        t_remote.daemon = True
        t_remote.start()

    if t_local:
        t_local.join()

    if t_remote:
        t_remote.join()

    print('Local index file:', dindex_local)
    print('Remote index file:', dindex_remote)
