from .utils import log_info, log_error


def pre(cmd, argv):
    return (cmd, argv, True)


def post(cmd, argv, result, output):
    if output[1]:
        log_error(output[1].decode('utf-8'), end="")
        return

    for line in sorted(output[0].decode('utf-8').rstrip('\n').split('\n')):
        line = line.rstrip()
        print(line)
