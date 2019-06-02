import sys

from .utils import (run, log_info, log_error)

from .worker import do_job


def main():
    global pre_cmd
    global post_cmd

    from . import task_queue

    sys.argv = sys.argv[1:]

    if len(sys.argv) == 0:
        exit(run(['drive']).returncode)

    cmd = sys.argv[0]
    argv = sys.argv[1:]

    if cmd in ('queue', 'q'):
        return task_queue.start()

    if cmd in ('pushq', 'pullq'):
        task_queue.add_task(cmd, argv)
        return

    try:
        return do_job(cmd, argv)
    except KeyboardInterrupt:
        log_error('KeyboardInterrupt')
        return 1
