import sys

from . import config
from . import drive_wrapper
from . import tq


def usage(cmd_name):
    print('Usage:')
    print('    tq')
    print('    d')
    print('    WIP')
    return 1


def main():
    config.load()

    argv = sys.argv[:]

    cmd_name = argv.pop(0)

    block = False
    notify = None

    while len(argv):
        if argv[0] in ('-h', '--help'):
            return usage(cmd_name)

        elif argv[0] in ('-m', '--mode'):
            argv.pop(0)
            mode = argv.pop(0)

        elif argv[0] in ('-b', '--block'):
            block = True
            argv.pop(0)

        elif argv[0] in ('-t', '--telegram'):
            notify = True
            argv.pop(0)

        elif argv[0] in ('-T', '--no-telegram'):
            notify = False
            argv.pop(0)

        else:
            break

    if notify is not None:
        config.set('telegram', 'enable', notify)
        config.save()

    if notify:
        telegram.enable()
        config.save()

    if mode == 'tq':
        tq.main(argv, block=block)

    elif mode == 'd':
        return drive_wrapper.main(argv)

    else:
        return usage(cmd_name)
