from os import getcwd

from . import hooks
from . import utils

from .task import Task
from .chain import Chain


def run(cmd, args):
    task_user = Task(cwd=getcwd(), cmd=cmd, args=args)
    task_exec = Task(cwd=getcwd(), cmd=utils.eff_cmd.get(cmd, cmd), args=args)

    hook_cbs = (Chain(dir(hooks))
        .filter(lambda x: x.startswith(('pre_', 'post_')))
        .map(lambda x: (x, getattr(hooks, x)))
        .dict())

    try:
        cap_out = False if not hook_cbs.get('pre_' + task_exec.cmd, lambda x: None)(task_exec) else True
        task_user.status = 'working'
        p = utils.run(['drive', task_exec.cmd] + task_exec.args, capture_output=cap_out)
        task_user.status = 'succeed' if (p.returncode == 0) else 'failed'
    except KeyboardInterrupt:
        task_user.status = 'interrupted'
        pass

    try:
        hook_cbs.get('post_' + task_exec.cmd, lambda *x: None)(task_user, p.stdout, p.stderr)
        return p.returncode
    except UnboundLocalError:
        hook_cbs.get('post_' + task_exec.cmd, lambda *x: None)(task_user, '', '')
        return 1
