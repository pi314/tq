import re
import subprocess as sub
import sys
import os

from subprocess import PIPE
from datetime import datetime
from os.path import exists, join


TICKET_PATH = '/tmp'


my_ticket = None
ticket_fname_matcher = re.compile(r'^dpush\.[0-9]+\.(\w+)\((\d+)\)$')


class Ticket:
    @classmethod
    def scan(cls):
        return sorted(
            map(lambda x: Ticket(tid=x),
                filter(
                    lambda x: ticket_fname_matcher.match(x),
                    os.listdir(TICKET_PATH)
                )
            )
        )

    def __init__(self, *, tid=None, cmd=None):
        if tid:
            self.tid = tid

        else:
            now = datetime.now()
            pid = os.getpid()
            self.tid = 'dpush.' + now.strftime('%Y%m%d%H%M%S') + '%06d.%s(%05d)' % (now.microsecond, cmd, pid)

        m = ticket_fname_matcher.match(self.tid)

        self.cmd = m.group(1)
        self.pid = m.group(2)

    def __str__(self):
        return self.tid

    def __hash__(self):
        return self.tid

    def __eq__(self, other):
        return self.tid == other.tid

    def __lt__(self, other):
        return self.tid < other.tid

    def create(self):
        with open(join(TICKET_PATH, str(self.tid)), 'w') as f:
            print('[alloc]', self.tid)

    def destroy(self):
        try:
            print('[free]', self.tid)
            os.remove(join(TICKET_PATH, str(self.tid)))
        except OSError as e:
            print(e)

    def exists(self):
        return exists(join(TICKET_PATH, self.tid))


def run(cmd, capture_output=False):
    kwargs = {
        'stdout': sys.stdout,
        'stderr': sys.stderr,
    }
    if capture_output:
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE

    return sub.run(cmd, **kwargs)


def ticket_alloc(cmd):
    global my_ticket

    if my_ticket:
        print(my_ticket)
        return

    my_ticket = Ticket(cmd=cmd)
    my_ticket.create()


def ticket_free():
    global my_ticket

    my_ticket.destroy()
    my_ticket = None


def ticket_wait(cmd=None):
    while True:
        tickets = Ticket.scan()

        if cmd:
            tickets = list(filter(lambda x: x == my_ticket or x.cmd in cmd, tickets))

        for i in tickets:
            print('[scan]', i)

        my_idx = tickets.index(my_ticket)

        if my_idx <= 0:
            return

        prev_ticket = tickets[my_idx - 1]
        prev_pid = prev_ticket.pid

        print('[wait]', prev_pid)
        sub.run(['caffeinate', '-w', prev_pid])

        try:
            if prev_ticket.exists():
                print('[orphen] {}'.format(prev_ticket))
                prev_ticket.destroy()
        except OSError as e:
            print(e)
