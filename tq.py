import sys

from os import getcwd

from . import config
from . import server
from . import client
from . import telegram
from . import logger

from .task import Task


def main(args):
    if args.telegram is not None:
        config.set('telegram', 'enable', args.telegram)
        config.save()

    if args.telegram:
        try:
            telegram.enable()
        except KeyboardInterrupt:
            exit(1)
        config.save()

    if args.load:
        return server.load(args.dry)

    if args.dump:
        return client.request_dump()

    if args.autoquit is not None:
        return client.set_autoquit(args.autoquit)

    if not len(args.cmd):
        return server.start()

    if len(args.cmd) and args.cmd[0] == 'd':
        logger.log_error('Use sub-command "d" instead')
        return 1

    t = Task(cwd=getcwd(), cmd=args.cmd[0], args=args.cmd[1:], block=args.block)
    return client.submit_task(t)
