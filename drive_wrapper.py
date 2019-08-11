from . import client
from . import drive_cmd
from . import drive_index
from . import utils


def main(argv):
    if len(argv) == 0:
        exit(utils.run(['drive']).returncode)

    d_cmd = argv.pop(0)

    if d_cmd == 'index':
        return drive_index.main(argv)

    if d_cmd in ('pushq', 'pullq'):
        return client.submit_task('d', [d_cmd] + argv, block=False)

    if d_cmd in ('pushw', 'pullw'):
        return client.submit_task('d', [d_cmd] + argv, block=True)

    return drive_cmd.run(d_cmd, argv)[1]
