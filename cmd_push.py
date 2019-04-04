from .utils import run


telegram_bot = 'cychih_bot'


def pre(cmd, argv):
    return (cmd, ['-no-prompt'] + argv, False)


def post(cmd, argv, p):
    if not p:
        res_str = 'interrupted'

    elif p.returncode == 0:
        res_str = 'succ'

    else:
        res_str = 'fail'

    try:
        run([
            telegram_bot,
            cmd +' '+ res_str +':\n' + '\n'.join(argv)
        ])
    except KeyboardInterrupt:
        pass
