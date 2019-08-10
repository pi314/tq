import sys

from . import config
from . import server
from . import client
from . import telegram


def usage():
    print('Usage:')
    print('    WIP')
    exit(1)


def main():
    sys.argv = sys.argv[1:]

    config.load()

    block = False
    notify = None

    while len(sys.argv):
        if sys.argv[0] in ('-h', '--help'):
            usage()

        elif sys.argv[0] in ('-b', '--block'):
            block = True
            sys.argv.pop(0)

        elif sys.argv[0] in ('-t', '--telegram'):
            notify = True
            sys.argv.pop(0)

        elif sys.argv[0] in ('-T', '--no-telegram'):
            notify = False
            sys.argv.pop(0)

        else:
            break

    if notify is not None:
        config.set('telegram', 'enable', notify)
        config.save()

    if notify:
        telegram.enable()
        config.save()

    if not len(sys.argv):
        return server.start()

    else:
        return client.submit_task(sys.argv, block)
