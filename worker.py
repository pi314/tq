from . import hooks

from .task import Task
from .utils import run
from .chain import Chain


def do_job(task_user):
    task_exec = task_user.copy()

    hook_cbs = (Chain(dir(hooks))
        .filter(lambda x: x.startswith(('pre_', 'post_')))
        .map(lambda x: (x, getattr(hooks, x)))
        .dict())

    if task_exec.cmd == 'quit':
        hook_cbs.get('pre_' + task_user.cmd, lambda x: None)(task_exec)
        task_user.status = 'succeed'
        hook_cbs.get('post_' + task_user.cmd, lambda *x: None)(task_user, '', '')
        return 0

    try:
        cap_out = False if not hook_cbs.get('pre_' + task_user.cmd, lambda x: None)(task_exec) else True
        task_user.status = 'working'
        p = run(['drive', task_exec.cmd] + task_exec.args, capture_output=cap_out)
        task_user.status = 'succeed' if (p.returncode == 0) else 'failed'
    except KeyboardInterrupt:
        task_user.status = 'interrupted'

    try:
        hook_cbs.get('post_' + task_user.cmd, lambda *x: None)(task_user, p.stdout, p.stderr)
        return p.returncode
    except UnboundLocalError:
        hook_cbs.get('post_' + task_user.cmd, lambda *x: None)(task_user, '', '')
        return 1
