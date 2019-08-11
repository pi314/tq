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
        return client.submit_task('d', [d_cmd] + args.cmd[1:], block=False)

    if d_cmd in ('pushw', 'pullw'):
        client.submit_task('d', [d_cmd] + args.cmd[1:], block=True)

    return drive_cmd.run(d_cmd, args.cmd[1:])[1]
