from os import getcwd

from . import lib_utils
from . import hooks

from .lib_chain import Chain
from .models import Task


def get_hook(cmd):
    hook_funcs = (Chain(dir(hooks))
        .filter(lambda x: x.startswith(('pre_', 'post_')))
        .map(lambda x: (x, getattr(hooks, x)))
        .dict())

    return hook_funcs.get(cmd, lambda *x: None)


def get_hook_pre(cmd):
    return get_hook('pre_' + cmd)


def get_hook_post(cmd):
    return get_hook('post_' + cmd)


def run(task):
    try:
        task.status = 'working'
        p = lib_utils.run(['drive', lib_utils.eff_cmd.get(task.args[0], task.args[0])] + task.args[1:], capture_output=task.cap_out)
        task.status = 'succeed' if (p.returncode == 0) else 'failed'
    except KeyboardInterrupt:
        task.status = 'interrupted'

    try:
        try:
            get_hook_post(task.args[0])(task, p.stdout, p.stderr)
            return p.returncode
        except UnboundLocalError:
            get_hook_post(task.args[0])(task, '', '')
            return 1

    except KeyboardInterrupt:
        return 1
