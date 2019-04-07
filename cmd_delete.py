from .utils import log_info, log_error


def pre(cmd, argv):
    log_info('Remap "delete" to "trash"')
    return ('trash', argv, False)
