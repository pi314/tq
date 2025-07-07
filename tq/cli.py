import argparse
import sys

from os.path import basename

from . import __version__
from . import api


def main():
    prog = basename(sys.argv[0])
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog=prog, description='tq')
    parser.add_argument('-v', '--version', action='version', version=f'tq {__version__}')

    args = parser.parse_args()

    print('tq wip')

    conn = api.connect()
    print(f'daemon pid = {conn.pid}')
    try:
        with conn:
            while True:
                data = conn.recv()
                print(data)
                if data == '[bye]':
                    break
                conn.send(input())
    except Exception as e:
        print(e)
