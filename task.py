class Task:
    def __init__(self, cwd, cmd, args, status='pending'):
        self.cwd = cwd
        self.cmd = cmd
        self.args = list(args)
        self.status = status

    def __str__(self):
        ret = []
        ret.append('['+ self.status +'] cwd:'+ str(self.cwd))
        ret.append('['+ self.status +'] cmd:'+ self.cmd)
        for i in self.args:
            ret.append('['+ self.status +'] arg:'+ i)

        return '\n'.join(ret)

    def copy(self):
        return Task(self.cwd, self.cmd, self.args, self.status)
