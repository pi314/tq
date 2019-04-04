import sys

from .utils import run


def d_cmd(cmd, argv):
    from . import cmd_dummy

    (cmd, argv, cap_out) = pre_cmd.get(cmd, cmd_dummy.pre)(cmd, argv)

    try:
        p = None
        p = run(['drive', cmd] + argv, capture_output=cap_out)
    except KeyboardInterrupt:
        pass

    post_cmd.get(cmd, cmd_dummy.post)(cmd, argv, p)

    return p.returncode if p else 1


def main():
    global pre_cmd
    global post_cmd

    from . import cmd_delete
    from . import cmd_push
    from . import cmd_list

    pre_cmd = {
            'delete': cmd_delete.pre,
            'list': cmd_list.pre,
            'push': cmd_push.pre,
            'pull': cmd_push.pre,
    }

    post_cmd = {
            'list': cmd_list.post,
            'push': cmd_push.post,
            'pull': cmd_push.post,
    }

    sys.argv = sys.argv[1:]

    if len(sys.argv) == 0:
        exit(run(['drive']).returncode)

    cmd = sys.argv[0]
    argv = sys.argv[1:]

    try:
        return d_cmd(cmd, argv)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        return 1
