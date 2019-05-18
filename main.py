import sys

from .utils import (run, log_info, log_error,
        ticket_alloc, ticket_free, ticket_wait, ticket_scan)


def d_cmd(cmd_user, argv_user):
    from . import cmd_dummy

    if cmd_user == 'wait':
        ticket_wait()
        return 0

    if cmd_user == 'tickets':
        ticket_scan()
        return 0

    ticket_alloc(cmd_user)

    try:
        result = 'canceled'
        (cmd_exec, argv_exec, cap_out) = pre_cmd.get(cmd_user, cmd_dummy.pre)(cmd_user, argv_user.copy())
        result = 'interrupted'
        p = run(['drive', cmd_exec] + argv_exec, capture_output=cap_out)
        result = 'succeed' if (p.returncode == 0) else 'failed'
    except KeyboardInterrupt:
        pass

    ticket_free()

    try:
        post_cmd.get(cmd_user, cmd_dummy.post)(cmd_user, argv_user, result, (p.stdout, p.stderr))
        return p.returncode
    except UnboundLocalError:
        post_cmd.get(cmd_user, cmd_dummy.post)(cmd_user, argv_user, result, ('', ''))
        return 1


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
        log_error('KeyboardInterrupt')
        return 1
