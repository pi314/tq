import os

from .utils import run


telegram_bot = 'cychih_bot'


def pre(cmd, argv):
    cmd = {
            'pushq': 'push',
            'pullq': 'pull',
            }.get(cmd, cmd)

    return (cmd, ['-no-prompt'] + argv, False)


def post(cmd, argv, result, output):
    try:
        run([
            telegram_bot,
            '\n'.join(['pwd: '+ os.getcwd(), cmd +' '+ result +':'] + argv)
        ])
    except KeyboardInterrupt:
        pass
