from .utils import log_info, log_error


def pre(cmd, argv):
    return (cmd, argv, True)


def post(cmd, argv, p):
    if not p:
        return

    if p.stderr:
        log_error(p.stderr.decode('utf-8'), end="")
        return

    output = p.stdout.decode('utf-8').rstrip('\n').split('\n')
    for line in sorted(output):
        line = line.rstrip()
        print(line)
