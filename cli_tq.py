import sys

from os import getcwd

from . import lib_config
from . import wire_server
from . import wire_client
from . import lib_telegram
from . import lib_logger
from . import lib_wire

from .models import Task


def main(args):
    if args.telegram is not None:
        lib_config.set('telegram', 'enable', args.telegram)
        lib_config.save()

    if args.telegram:
        try:
            lib_telegram.enable()
        except KeyboardInterrupt:
            exit(1)
        lib_config.save()

    if args.load:
        return wire_server.load(args.dry)

    if args.dump:
        return wire_client.request_dump()

    if args.autoquit is not None:
        return wire_client.set_autoquit(args.autoquit)

    if not len(args.cmd):
        return wire_server.start()

    if len(args.cmd) and args.cmd[0] == 'd':
        lig_logger.log_error('Use sub-command "d" instead')
        return 1

    t = Task(cwd=getcwd(), cmd=args.cmd[0], args=args.cmd[1:], block=args.block)
    return wire_client.submit_task(t)
