import sys

import subprocess as sub
from subprocess import PIPE


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
