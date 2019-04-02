#!/usr/bin/env python

import sys
import subprocess as sub
from subprocess import PIPE


telegram_bot = 'cychih_bot'


def run(cmd, capture_output=False):
    kwargs = {
        'stdout': sys.stdout,
        'stderr': sys.stderr,
    }
    if capture_output:
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE

    return sub.run(cmd, **kwargs)


def d_list(argv):
    p = run(['drive', 'list'] + argv, capture_output=True)
    if p.stderr:
        print(p.stderr.decode('utf-8'), end="")
        return 1
    else:
        output = p.stdout.decode('utf-8').rstrip('\n').split('\n')
        for line in sorted(output):
            line = line.rstrip()
            print(line)

    return p.returncode


def d_push(argv):
    try:
        p = run(['drive', 'push', '-no-prompt'] + argv)
        res_str = 'succ' if p.returncode == 0 else 'fail'
        ret = p.returncode
    except KeyboardInterrupt:
        res_str = 'interrupted'
        ret = 1

    try:
        run([
            telegram_bot,
            'push '+ res_str +':\n' + '\n'.join(argv)
        ])
    except KeyboardInterrupt:
        pass

    return ret


def d_pull(argv):
    try:
        p = run(['drive', 'pull', '-no-prompt'] + argv)
        res_str = 'succ' if p.returncode == 0 else 'fail'
        ret = p.returncode
    except KeyboardInterrupt:
        res_str = 'interrupted'
        ret = 1

    try:
        run([
            telegram_bot,
            'pull '+ res_str +':\n' + '\n'.join(argv)
        ])
    except KeyboardInterrupt:
        pass

    return ret


def d_trash(argv):
    print('Remap "delete" to "trash"')
    p = run(['drive', 'trash'] + argv)
    return p.returncode


def d_cmd(cmd, argv):
    p = run(['drive', cmd] + argv)
    return p.returncode


def main():
    sys.argv = sys.argv[1:]

    if len(sys.argv) == 0:
        exit(run(['drive']).returncode)

    cmd = sys.argv[0]
    argv = sys.argv[1:]

    if cmd == 'list':
        return d_list(argv)

    if cmd == 'push':
        return d_push(argv)

    if cmd == 'pull':
        return d_pull(argv)

    if cmd == 'delete':
        return d_trash(argv)

    if cmd in ('open', 'rename', 'move', 'mv'):
        return d_cmd(cmd, argv)

    print('Unknown command:', cmd)

    return 1


exit(main())
