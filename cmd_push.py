import os

from threading import Thread

from .utils import run


telegram_bot = 'cychih_bot'


def pre(cmd, argv):
    cmd = {
            'pushq': 'push',
            'pullq': 'pull',
            }.get(cmd, cmd)

    return (cmd, ['-no-prompt'] + argv, False)


def send_telegram_msg(cmd, argv, result, output):
    run([
        telegram_bot,
        '\n'.join(['pwd: '+ os.getcwd(), cmd +' '+ result +':'] + argv)
    ])


def post(cmd, argv, result, output):
    try:
        if cmd.endswith('q'):
            t = Thread(target=send_telegram_msg, args=(cmd, argv, result, output))
            t.daemon = True
            t.start()
        else:
            send_telegram_msg(cmd, argv, result, output)
    except KeyboardInterrupt:
        pass
