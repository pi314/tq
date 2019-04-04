from .utils import run, ticket_wait


telegram_bot = 'cychih_bot'


def pre(cmd, argv):
    ticket_wait(('push', 'pushw', 'pull', 'pullw'))

    cmd = {
            'pushw': 'push',
            'pullw': 'pull',
            }.get(cmd, cmd)

    return (cmd, ['-no-prompt'] + argv, False)
