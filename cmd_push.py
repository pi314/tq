import os

from .utils import run


telegram_bot = 'cychih_bot'


def pre(cmd, argv):
    return (cmd, ['-no-prompt'] + argv, False)


def post(cmd, argv, result, output):
    try:
        run([
            telegram_bot,
            '\n'.join(['pwd: '+ os.getcwd(), cmd +' '+ result +':'] + argv)
        ])
    except KeyboardInterrupt:
        pass
