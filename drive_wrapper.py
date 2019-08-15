from os import getcwd

from . import client
from . import drive_cmd
from . import drive_index
from . import hooks
from . import utils

from .task import Task


def main(args):
    if len(args.cmd) == 0:
        exit(utils.run(['drive']).returncode)

    d_cmd = args.cmd[0]

    if d_cmd == 'index': # Should it be a special case?
        return drive_index.main(args.cmd[1:])

    task = Task(cwd=getcwd(), cmd='d', args=args.cmd, block=False)

    task_list = drive_cmd.get_hook_pre(task.args[0])(task)

    if not task_list:
        task_list = [task]

    for task in task_list:
        if task.block == Task.NORMAL:
            ret = drive_cmd.run(task)

        if task.block == Task.QUEUE:
            ret = client.submit_task(task)

        if task.block == Task.BLOCK:
            ret = client.submit_task(task)
            if ret == 0:
                ret = drive_cmd.run(task)

        if ret != 0:
            return ret
