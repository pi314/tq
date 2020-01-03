import subprocess as sub
import sys

from os import getcwd
from os.path import join, exists, dirname, isfile
from subprocess import PIPE


eff_cmd = {
    'pushq': 'push',
    'pullq': 'pull',
    'pushw': 'push',
    'pullw': 'pull',
    'renameq': 'rename',
}


def ask(prompt, given_options=''):
    '''
    ask(prompt)
    ask(prompt, ['y', 'n'])
    ask(prompt, 'yn')
    ask(prompt, 'yes no')
    '''

    if isinstance(given_options, str):
        options = given_options.split()
        if len(options) == 1:
            options = [c for c in given_options]

    elif isinstance(given_options, list):
        options = given_options

    options = [o.lower() for o in options]
    if options:
        options[0] = options[0][0].upper() + options[0][1:]

    if options == []:   # str input
        try:
            return input(prompt + '> ')
        except EOFError:
            return None

    try:
        ret = input('{prompt} [{opts}] '.format(
            prompt=prompt,
            opts='/'.join(options)
        )).strip().lower()

        if ret == '':
            ret = options[0]

        else:
            matches = list(filter(lambda x: x.startswith(ret), map(str.lower, options)))
            if len(matches) == 0:
                ret = None
            else:
                ret = matches[0]

    except EOFError:
        return None

    return ret.lower()


def run(cmd, capture_output=False):
    kwargs = {
        'stdout': sys.stdout,
        'stderr': sys.stderr,
    }
    if capture_output:
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE

    return sub.run(map(str, cmd), **kwargs)


def get_drive_root(cwd=None):
    probe = cwd if cwd else getcwd()

    while probe != '/':
        if exists(join(probe, '.gd')) and isfile(join(probe, '.gd', 'credentials.json')):
            return probe

        probe = dirname(probe)

    return None
