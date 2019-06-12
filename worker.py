from .hooks import pre_dummy, post_dummy
from .hooks import pre_delete
from .hooks import pre_list, post_list
from .hooks import pre_push, post_push

from .task import Task
from .utils import run


pre_cmd = {
        'delete': pre_delete,
        'list': pre_list,
        'push': pre_push,
        'pull': pre_push,
        'pushq': pre_push,
        'pullq': pre_push,
        'quit': pre_dummy,
}

post_cmd = {
        'list': post_list,
        'push': post_push,
        'pull': post_push,
        'pushq': post_push,
        'pullq': post_push,
        'quit': post_push,
}


def do_job(task_user):
    task_exec = task_user.copy()

    if task_exec.cmd == 'quit':
        pre_cmd.get(task_user.cmd, pre_dummy)(task_exec)
        task_user.status = 'succeed'
        post_cmd.get(task_user.cmd, post_dummy)(task_user, '', '')
        return 0

    try:
        cap_out = False if not pre_cmd.get(task_user.cmd, pre_dummy)(task_exec) else True
        task_user.status = 'working'
        p = run(['drive', task_exec.cmd] + task_exec.args, capture_output=cap_out)
        task_user.status = 'succeed' if (p.returncode == 0) else 'failed'
    except KeyboardInterrupt:
        task_user.status = 'interrupted'

    try:
        post_cmd.get(task_user.cmd, post_dummy)(task_user, p.stdout, p.stderr)
        return p.returncode
    except UnboundLocalError:
        post_cmd.get(task_user.cmd, post_dummy)(task_user, '', '')
        return 1
