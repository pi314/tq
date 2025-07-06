import argparse
import sys

from os.path import basename

from . import __version__


def main():
    prog = basename(sys.argv[0])
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog=prog, description='tq')

    print(__version__)
    print('tq wip')
    sys.exit(1)
