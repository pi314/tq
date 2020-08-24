from os import getcwd

from . import wire_client
from . import lib_drive_cmd
from . import lib_drive_cmd_index
from . import lib_utils
from . import lib_wire

from .models import Task


def main(args):
    if len(args.cmd) == 0:
        exit(lib_utils.run(['drive']).returncode)

    d_cmd = args.cmd[0]

    if d_cmd == 'index': # Should it be a special case?
        return lib_drive_cmd_index.main(args.cmd[1:])

    task = Task(tid=Task.gen_tid(), cwd=getcwd(), cmd='d', args=args.cmd, block=False)

    task_list = lib_drive_cmd.get_hook_pre(task.args[0])(task)

    if not task_list:
        task_list = [task]

    for task in task_list:
        if task.block == Task.LOCAL:
            ret = lib_drive_cmd.run(task)

        if task.block == Task.QUEUE:
            ret = wire_client.submit_task(task)

        if task.block == Task.BLOCK:
            ret = wire_client.submit_task(task)
            if ret == 0:
                ret = lib_drive_cmd.run(task)

        if ret != 0:
            return ret
