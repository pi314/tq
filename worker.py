from .hooks import pre_dummy, post_dummy
from .hooks import pre_delete
from .hooks import pre_list, post_list
from .hooks import pre_push_pull, post_push_pull
from .hooks import pre_rename

from .task import Task
from .utils import run


pre_cmd = {
        'delete': pre_delete,
        'list': pre_list,
        'push': pre_push_pull,
        'pull': pre_push_pull,
        'pushq': pre_push_pull,
        'pullq': pre_push_pull,
        'rename': pre_rename,
        'quit': pre_dummy,
}

post_cmd = {
        'list': post_list,
        'push': post_push_pull,
        'pull': post_push_pull,
        'pushq': post_push_pull,
        'pullq': post_push_pull,
        'quit': post_push_pull,
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
