import re
import subprocess as sub

from os import getcwd
from os import walk
from os.path import join
from threading import Thread

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


def indexing_local(cwd, root, driveignore):
    print('Indexing local files ...')

    plist = []
    for root, subdirs, files in walk(cwd):
        for f in files:
            if ignore_fname(driveignore, f):
                continue

            plist.append(join(root, f)[len(cwd)+1:])

    with open(dindex_local, 'wb') as f:
        for p in sorted(plist):
            writeline(f, p)

    print('Indexing local files ... Done')


def indexing_remote(cwd, root, driveignore):
    print('Indexing remote files ...')

    p = sub.Popen('drive list -files -recursive -no-prompt'.split(), stdout=sub.PIPE)

    plist = []
    for line in iter(p.stdout.readline, b''):
        line = line.decode('utf-8').rstrip('\n')
        if not line: continue

        if line.startswith('/'):
            line = line[1:]

        plist.append(join(root, line)[len(cwd)+1:])

    with open(dindex_remote, 'wb') as f:
        for p in sorted(plist):
            writeline(f, p)

    print('Indexing remote files ... Done')


def indexing(argv):
    # todo: read /.driveignore
    # todo: support -depth <n>

    cwd = getcwd()
    root = get_drive_root()
    driveignore = []

    if not root:
        log_error('Drive context not found')
        return 1

    with open(join(root, '.driveignore')) as f:
        for line in f:
            line = line.rstrip('\n')
            driveignore.append(re.compile(line))

    indexing_args = (cwd, root, driveignore)

    t_local = Thread(target=indexing_local, args=indexing_args)
    t_local.daemon = True
    t_local.start()

    t_remote = Thread(target=indexing_remote, args=indexing_args)
    t_remote.daemon = True
    t_remote.start()

    t_local.join()
    t_remote.join()

    print('Local index file:', dindex_local)
    print('Remote index file:', dindex_remote)
