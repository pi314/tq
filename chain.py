class Chain(list):
    def __init__(self, data):
        self.data = data

    def map(self, m):
        return Chain(map(m, self.data))

    def filter(self, f):
        return Chain(filter(f, self.data))

    def sorted(self):
        return sorted(self.data)

    def list(self):
        return self.data
