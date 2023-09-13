from collections import deque

class History:
    def __init__(self, size=50):
        self.data = deque(maxlen=size)

    def append(self, val):
        self.data.append(val)

    def first(self):
        return self.data[-1] if self.data else None  # Most recently added game

    def last(self):
        return self.data[0] if self.data else None  # Oldest game

    def toArray(self):
        return list(self.data)