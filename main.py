import sys
import os

from . import task_queue

from .utils import (run, log_error)
from .task import Task
from .worker import do_job
from .cmd_index import build_index


def main():
    sys.argv = sys.argv[1:]

    if len(sys.argv) == 0:
        exit(run(['drive']).returncode)

    cmd = sys.argv[0]
    argv = sys.argv[1:]

    if cmd in ('queue', 'q'):
        if not argv:
            return task_queue.start()

        elif argv[0] == 'dumpjson':
            return task_queue.dumpjson()

        elif argv[0] == 'dump':
            return task_queue.dump()

        elif argv[0] == 'load':
            return task_queue.load()

        elif argv[0] == 'quit':
            return task_queue.schedule_quit()

        else:
            log_error('Unknown command')
            return 1

    elif cmd in ('pushq', 'pullq'):
        task_queue.add_task(cmd, argv)
        return

    elif cmd == 'index':
        return build_index(argv)

    try:
        task = Task(os.getcwd(), cmd, argv, 'working')
        return do_job(task)
    except KeyboardInterrupt:
        log_error('KeyboardInterrupt')
        return 1
