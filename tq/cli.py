import argparse
import sys
import os

from os.path import basename

from . import __version__
from . import tq


def main():
    prog = basename(sys.argv[0])
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog=prog, description='tq')
    parser.add_argument('-v', '--version', action='version', version=f'tq {__version__}')

    args = parser.parse_args()

    print(f'my pid = {os.getpid()}')

    conn = tq.connect()
    if not conn:
        print('Connection failed')
        sys.exit(1)

    print(f'daemon pid = {conn.pid}')
    try:
        with conn:
            while conn:
                i = input().strip()
                if i == '':
                    print('bye')
                    tq.bye()
                    break
                elif i in ('quit', 'stop', 'shutdown'):
                    res = tq.shutdown()
                else:
                    res = tq.echo(msg=i)

                if res.res is None:
                    print(res)
                    break

                print(res)

    except Exception as e:
        raise e
