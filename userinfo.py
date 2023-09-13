import STPyV8

class UserInfo(STPyV8.JSClass):
    def __init__(self, username, balance):
        self.uname = username
        self.balance = balance
        self.wagers = 0
        self.wagered = 0
        self.profit = 0