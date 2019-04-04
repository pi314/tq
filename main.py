#!/usr/bin/env python

import sys
import subprocess as sub
from subprocess import PIPE


telegram_bot = 'cychih_bot'


def run(cmd, capture_output=False):
    print(cmd)
    kwargs = {
        'stdout': sys.stdout,
        'stderr': sys.stderr,
    }
    if capture_output:
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE

    return sub.run(cmd, **kwargs)


def pre_cmd_dummy(cmd, argv):
    return (cmd, argv, False)


def pre_cmd_delete(cmd, argv):
    print('Remap "delete" to "trash"')
    return ('trash', argv, False)


def pre_cmd_list(cmd, argv):
    return (cmd, argv, True)


def pre_cmd_push_pull(cmd, argv):
    return (cmd, ['-no-prompt'] + argv, False)


def d_cmd(cmd, argv):
    (cmd, argv, cap_out) = pre_cmd.get(cmd, pre_cmd_dummy)(cmd, argv)

    try:
        p = None
        p = run(['drive', cmd] + argv, capture_output=cap_out)
    except KeyboardInterrupt:
        pass

    post_cmd.get(cmd, post_cmd_dummy)(cmd, argv, p)

    return p.returncode if p else 1


def post_cmd_dummy(cmd, argv, p):
    pass


def post_cmd_list(cmd, argv, p):
    if not p:
        return

    if p.stderr:
        print(p.stderr.decode('utf-8'), end="")
        return

    output = p.stdout.decode('utf-8').rstrip('\n').split('\n')
    for line in sorted(output):
        line = line.rstrip()
        print(line)


def post_cmd_push_pull(cmd, argv, p):
    if not p:
        res_str = 'interrupted'

    elif p.returncode == 0:
        res_str = 'succ'

    else:
        res_str = 'fail'

    try:
        run([
            telegram_bot,
            cmd +' '+ res_str +':\n' + '\n'.join(filter(lambda x: x != '-no-prompt', argv))
        ])
    except KeyboardInterrupt:
        pass


def main():
    global pre_cmd
    global post_cmd

    pre_cmd = {
            'delete': pre_cmd_delete,
            'list': pre_cmd_list,
            'push': pre_cmd_push_pull,
            'pull': pre_cmd_push_pull,
    }

    post_cmd = {
            'list': post_cmd_list,
            'push': post_cmd_push_pull,
            'pull': post_cmd_push_pull,
    }

    sys.argv = sys.argv[1:]

    if len(sys.argv) == 0:
        exit(run(['drive']).returncode)

    cmd = sys.argv[0]
    argv = sys.argv[1:]

    try:
        return d_cmd(cmd, argv)
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        return 1

