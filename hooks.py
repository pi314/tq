import os

from threading import Thread

from .utils import log_info, log_error
from .utils import run
from .utils import send_telegram_msg


def pre_dummy(cmd, argv):
    return (cmd, argv, False)


def post_dummy(cmd, argv, *args):
    pass


def pre_delete(cmd, argv):
    log_info('Remap "delete" to "trash"')
    return ('trash', argv, False)


def pre_list(cmd, argv):
    return (cmd, argv, True)


def post_list(cmd, argv, result, output):
    if output[1]:
        log_error(output[1].decode('utf-8'), end="")
        return

    for line in sorted(output[0].decode('utf-8').rstrip('\n').split('\n')):
        line = line.rstrip()
        print(line)


def pre_push(cmd, argv):
    cmd = {
            'pushq': 'push',
            'pullq': 'pull',
            }.get(cmd, cmd)

    return (cmd, ['-no-prompt'] + argv, False)


def post_push(cmd, argv, result, output):
    try:
        if cmd.endswith('q'):
            t = Thread(target=send_telegram_msg, args=(cmd, argv, result, output))
            t.daemon = True
            t.start()
        else:
            send_telegram_msg(cmd, argv, result, output)
    except KeyboardInterrupt:
        pass
