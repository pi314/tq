import argparse
import sys

from os.path import basename

from . import __version__

from . import core_server


def main():
    prog = basename(sys.argv[0])
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog=prog, description='tq')
    parser.add_argument('-v', '--version', action='version', version=f'tq {__version__}')

    args = parser.parse_args()

    print('tq wip')

    from .core_daemon import spawn
    print(f'daemon pid = {spawn(core_server.serve)}')
