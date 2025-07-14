import argparse
import sys
import os

from os.path import basename

from . import __version__
from . import tq_api


def main():
    prog = basename(sys.argv[0])
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog=prog, description='tq')
    parser.add_argument('--version', action='version', version=f'tq {__version__}')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('cmd', nargs='*')

    args = parser.parse_args()

    print(f'my pid = {os.getpid()}')

    conn = tq_api.connect()
    if not conn:
        print('Connection failed')
        sys.exit(1)

    print(f'daemon pid = {conn.pid}')
    try:
        with conn:
            if args.cmd:
                if args.cmd[0] in ('quit', 'shutdown'):
                    res = tq_api.shutdown()
                    print(res)

                elif args.cmd[0] == 'cancel':
                    res = tq_api.cancel(args.cmd[1])
                    print(res)

                elif args.cmd[0] == 'list':
                    for res in tq_api.list():
                        print(res)

                else:
                    res = tq_api.enqueue(args.cmd)
                    print(res)

            else:
                while conn:
                    i = input('> ').strip()
                    if i == '':
                        print('bye')
                        tq_api.bye()
                        break

                    elif i in ('quit', 'stop', 'shutdown'):
                        res = tq_api.shutdown()

                    elif i in ('ls', 'list'):
                        for res in tq_api.list():
                            print(res)
                        continue

                    else:
                        res = tq_api.echo(msg=i)

                    if res.res is None:
                        print(res)
                        break

                    print(res)

    except (KeyboardInterrupt, EOFError) as e:
        pass
    except (Exception, KeyboardInterrupt, SystemExit) as e:
        raise e
