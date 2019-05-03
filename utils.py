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


def log_info(*args, **kwargs):
    if sys.stdout.isatty():
        print(*args, **kwargs)
    else:
        with open('/dev/tty', 'w') as tty:
            stdout_backup, sys.stdout = sys.stdout, tty
            print(*args, **kwargs, file=tty)
            sys.stdout = stdout_backup


def log_error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


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
            self.tid = 'dpush.' + now.strftime('%Y%m%d%H%M%S') + '%06d.%s(%d)' % (now.microsecond, cmd, pid)

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
            log_info('[alloc]', self.tid)

    def destroy(self):
        try:
            log_info('[free]', self.tid)
            os.remove(join(TICKET_PATH, str(self.tid)))
        except OSError as e:
            log_error(e)

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
        log_info(my_ticket)
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
            log_info('[scan]', i)

        if my_ticket:
            my_idx = tickets.index(my_ticket)

            if my_idx <= 0:
                my_idx = len(tickets)

        else:
            my_idx = len(tickets)

        try:
            prev_ticket = tickets[my_idx - 1]
        except IndexError:
            return

        prev_pid = prev_ticket.pid

        log_info('[wait]', prev_pid)
        sub.run(['caffeinate', '-w', prev_pid])

        try:
            if prev_ticket.exists():
                log_info('[orphen] {}'.format(prev_ticket))
                prev_ticket.destroy()
        except OSError as e:
            log_error(e)


def ticket_scan():
    tickets = Ticket.scan()
    for i in tickets:
        log_info('[scan]', i)
