import collections
from settings import HISTORY_LIMIT

class History:
    def __init__(self):
        self.history = collections.deque(maxlen=HISTORY_LIMIT)

    def add_to_history(self, interaction):
        self.history.append(interaction)

    def get_history(self):
        return list(self.history)
