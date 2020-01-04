import json
import os
import re
import socket
import socketserver
import subprocess as sub
import sys

from datetime import datetime
from queue import Queue
from threading import Thread
from time import sleep

from . import HOST, PORT
from . import lib_config
from . import lib_drive_cmd
from . import lib_telegram

from .models import Task
from .lib_logger import *
from .lib_utils import *


task_queue = Queue()
current_task = None

auto_quit_config = 60
auto_quit_remain = auto_quit_config


def submit_task_list(task_list):
    for task in task_list:
        if task.lock:
            task.status = 'blocking'
        else:
            task.status = 'pending'

        log_task(task)
        task_queue.put(task)


def get_task_list():
    return ([current_task], [])[current_task is None] + list(task_queue.queue)


def set_auto_quit(timeout):
    global auto_quit_config
    global auto_quit_remain

    m = re.match(r'^(\d+)([msh])$', timeout)
    if not m:
        return

    auto_quit_config = int(m.group(1)) * {'s': 1, 'm': 60, 'h': 3600}[m.group(2)]
    auto_quit_remain = auto_quit_config
    print('auto_quit={}, remain={}'.format(*get_auto_quit()))


def get_auto_quit():
    global auto_quit_config
    global auto_quit_remain

    return (auto_quit_config, auto_quit_remain)


def start():
    global current_task
    global auto_quit_config
    global auto_quit_remain

    v = sys.version_info
    log_sys('start', 'Python {}.{}.{}, releaselevel={}, serial={}'.format(
        v.major, v.minor, v.micro,
        v.releaselevel, v.serial
        ))

    try:
        while True:
            if task_queue.empty():
                if auto_quit_config == 0:
                    pass
                else:
                    auto_quit_remain -= 1
                    if auto_quit_remain <= 0:
                        break

                if auto_quit_remain % 5 == 0:
                    print('auto_quit={}, remain={}'.format(*get_auto_quit()))

                sleep(1)
                continue

            current_task = task_queue.get()
            auto_quit_remain = auto_quit_config

            if current_task.cmd == 'quit':
                current_task.status = 'succeed'
                log_task(current_task)
                lib_telegram.notify_task(current_task)
                break

            if current_task.lock:
                current_task.lock.notify()
                current_task.status = 'unblocked'
                log_task(current_task)
                lib_telegram.notify_task(current_task)

            else:
                current_task.status = 'working'
                log_task(current_task)
                lib_telegram.notify_task(current_task)

                os.chdir(current_task.cwd)
                if current_task.cmd == 'd':
                    ret = lib_drive_cmd.run(current_task)
                    log_task(current_task)
                    if current_task.status == 'interrupted':
                        raise KeyboardInterrupt

                else:
                    try:
                        p = sub.run([current_task.cmd] + current_task.args)
                        current_task.status = 'failed' if p.returncode else 'succeed'
                        current_task.ret = p.returncode
                    except FileNotFoundError:
                        current_task.status = 'error'

                    log_task(current_task)
                    lib_telegram.notify_task(current_task)

            current_task = None

            if task_queue.empty():
                log_sys('empty', 'auto_quit={}, remain={}'.format(*get_auto_quit()))
                lib_telegram.notify_msg(
                        '[status] empty: auto_quit={}, remain={}'.format(*get_auto_quit()))

    except KeyboardInterrupt:
        log_sys('stop', 'KeyboardInterrupt')
        ret = 1
