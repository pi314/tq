import sys

from . import config
from . import server
from . import client
from . import telegram


def main(argv, block):
    if not len(argv):
        return server.start()

    else:
        return client.submit_task(argv[0], argv[1:], block=block)
