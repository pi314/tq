from . import cmd_delete
from . import cmd_push
from . import cmd_list

from .utils import run


pre_cmd = {
        'delete': cmd_delete.pre,
        'list': cmd_list.pre,
        'push': cmd_push.pre,
        'pull': cmd_push.pre,
        'pushq': cmd_push.pre,
        'pullq': cmd_push.pre,
}

post_cmd = {
        'list': cmd_list.post,
        'push': cmd_push.post,
        'pull': cmd_push.post,
        'pushq': cmd_push.post,
        'pullq': cmd_push.post,
}


def do_job(cmd_user, argv_user):
    from . import cmd_dummy

    try:
        result = 'canceled'
        (cmd_exec, argv_exec, cap_out) = pre_cmd.get(cmd_user, cmd_dummy.pre)(cmd_user, argv_user.copy())
        result = 'interrupted'
        p = run(['drive', cmd_exec] + argv_exec, capture_output=cap_out)
        result = 'succeed' if (p.returncode == 0) else 'failed'
    except KeyboardInterrupt:
        pass

    try:
        post_cmd.get(cmd_user, cmd_dummy.post)(cmd_user, argv_user, result, (p.stdout, p.stderr))
        return (result, p.returncode)
    except UnboundLocalError:
        post_cmd.get(cmd_user, cmd_dummy.post)(cmd_user, argv_user, result, ('', ''))
        return (result, 1)
