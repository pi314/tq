import sys

from . import config
from . import drive_wrapper
from . import tq


def usage(cmd_name):
    print('Usage:')
    print('    tq')
    print('    tq load [-n]')
    print('    d')
    return 1


def main():
    config.load()

    argv = sys.argv[:]

    cmd_name = argv.pop(0)

    while len(argv):
        if argv[0] in ('-h', '--help'):
            return usage(cmd_name)

        elif argv[0] in ('-m', '--mode'):
            argv.pop(0)
            mode = argv.pop(0)

        else:
            break

    if mode == 'tq':
        tq.main(argv)

    elif mode == 'd':
        return drive_wrapper.main(argv)

    else:
        return usage(cmd_name)
