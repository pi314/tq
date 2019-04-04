import sys

from .utils import run, ticket_alloc, ticket_free


def d_cmd(cmd_user, argv_user):
    from . import cmd_dummy

    ticket_alloc(cmd_user)
    (cmd_exec, argv_exec, cap_out) = pre_cmd.get(cmd_user, cmd_dummy.pre)(cmd_user, argv_user.copy())

    try:
        p = None
        p = run(['drive', cmd_exec] + argv_exec, capture_output=cap_out)
    except KeyboardInterrupt:
        pass

    ticket_free()
    post_cmd.get(cmd_user, cmd_dummy.post)(cmd_user, argv_user, p)

    return p.returncode if p else 1


def main():
    global pre_cmd
    global post_cmd

    from . import cmd_delete
    from . import cmd_push
    from . import cmd_pushw
    from . import cmd_list

    pre_cmd = {
            'delete': cmd_delete.pre,
            'list': cmd_list.pre,
            'push': cmd_push.pre,
            'pull': cmd_push.pre,
            'pushw': cmd_pushw.pre,
            'pullw': cmd_pushw.pre,
    }

    post_cmd = {
            'list': cmd_list.post,
            'push': cmd_push.post,
            'pull': cmd_push.post,
            'pushw': cmd_push.post,
            'pullw': cmd_push.post,
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
