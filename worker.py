from .hooks import pre_dummy, post_dummy
from .hooks import pre_delete
from .hooks import pre_list, post_list
from .hooks import pre_push, post_push

from .utils import run


pre_cmd = {
        'delete': pre_delete,
        'list': pre_list,
        'push': pre_push,
        'pull': pre_push,
}

post_cmd = {
        'list': post_list,
        'push': post_push,
        'pull': post_push,
}


def do_job(cmd_user, argv_user):
    try:
        result = 'canceled'
        (cmd_exec, argv_exec, cap_out) = pre_cmd.get(cmd_user, pre_dummy)(cmd_user, argv_user.copy())
        result = 'interrupted'
        p = run(['drive', cmd_exec] + argv_exec, capture_output=cap_out)
        result = 'succeed' if (p.returncode == 0) else 'failed'
    except KeyboardInterrupt:
        pass

    try:
        post_cmd.get(cmd_user, post_dummy)(cmd_user, argv_user, result, (p.stdout, p.stderr))
        return (result, p.returncode)
    except UnboundLocalError:
        post_cmd.get(cmd_user, post_dummy)(cmd_user, argv_user, result, ('', ''))
        return (result, 1)
