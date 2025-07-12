class Task:
    def __init__(self, task_id, cmd, cwd=None, env=None):
        self.task_id = task_id
        self.cmd = cmd
        self.cwd = cwd
        self.env = env

    def __repr__(self):
        return f'Task(cmd={self.cmd})'
