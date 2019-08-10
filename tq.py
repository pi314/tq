import sys

from . import config
from . import server
from . import client
from . import telegram


def main(argv):
    block = False
    notify = None

    while len(argv):
        if argv[0] in ('-b', '--block'):
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

    if not len(argv):
        return server.start()

    else:
        return client.submit_task(argv[0], argv[1:], block=block)
