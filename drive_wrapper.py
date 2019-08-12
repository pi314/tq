from . import client
from . import drive_cmd
from . import drive_index
from . import utils


def main(args):
    if len(args.cmd) == 0:
        exit(utils.run(['drive']).returncode)

    d_cmd = args.cmd[0]

    if d_cmd == 'index':
        return drive_index.main(args.cmd[1:])

    if d_cmd in ('pushq', 'pullq'):
        args.cmd = ['d'] + args.cmd
        args.block = False
        return client.submit_task(args)

    if d_cmd in ('pushw', 'pullw'):
        args.cmd = ['d'] + args.cmd
        args.block = True
        client.submit_task(args)

    return drive_cmd.run(d_cmd, args.cmd[1:])[1]
