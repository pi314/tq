import sys

from os import getcwd
from threading import Thread

from . import lib_config
from . import wire_server
from . import wire_client
from . import lib_telegram
from . import lib_wire
from . import task_queue

from .lib_logger import *

from .models import Task


def main(args):
    if args.telegram is not None:
        lib_config.set('telegram', 'enable', args.telegram)
        lib_config.save()

    if args.telegram:
        try:
            lib_telegram.enable()
        except KeyboardInterrupt:
            exit(1)
        lib_config.save()

    task_list = []
    if args.load:
        task_list = load_task_list()
        if args.dry:
            for task in task_list:
                print()
                print(task)
            return 0

    if args.dump:
        return wire_client.get_task_list()

    if args.auto_quit is not None:
        return wire_client.set_auto_quit(args.auto_quit)

    if not len(args.cmd):
        log_create()

        th_wire_server = Thread(target=wire_server.start)
        th_wire_server.daemon = True
        th_wire_server.start()

        th_telegram_queue = Thread(target=lib_telegram.start)
        th_telegram_queue.daemon = True
        th_telegram_queue.start()

        if task_list:
            task_queue.submit_task_list(task_list)

        ret = task_queue.start()

        lib_telegram.loop_stop()
        th_telegram_queue.join()
        return ret

    if len(args.cmd) and args.cmd[0] == 'd':
        print_error('error', 'Use sub-command "d" instead')
        return 1

    t = Task(Task.gen_tid(), cwd=getcwd(), cmd=args.cmd[0], args=args.cmd[1:], block=args.block)
    return wire_client.submit_task(t)


def load_task_list():
    acc_log = {}

    fname = lib_config.get('log', 'filename')
    if not exists(fname):
        return start()

    with open(fname) as f:
        for line in f:
            try:
                log_entry = json.loads(line)
            except json.decoder.JSONDecodeError:
                pass

            if 'tid' in log_entry and 'status' in log_entry:
                acc_log[log_entry['tid']] = log_entry

    acc_log = dict(
            filter(
                lambda x:
                    x[1]['block'] == False and
                    x[1]['status'] not in ('failed', 'succeed', 'blocking', 'unblocked'),
                acc_log.items()
                )
            )

    task_list = []

    for tid in sorted(acc_log):
        e = acc_log[tid]
        t = Task(tid=e['tid'], cwd=e['cwd'], cmd=e['cmd'], args=e['args'], block=False)
        t.status = 'pending'

        task_list.append(t)

    return task_list
