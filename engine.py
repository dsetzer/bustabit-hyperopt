from pyee import AsyncIOEventEmitter
from userinfo import UserInfo
from history import History

class UserInfo:
    def __init__(self, uname, balance, wagered, profit, bets):
        self.uname = uname
        self.balance = balance
        self.wagered = wagered
        self.profit = profit
        self.bets = bets

    def __str__(self):
        return f"UserInfo(uname={self.uname}, balance={self.balance}, wagered={self.wagered}, profit={self.profit}, bets={self.bets})"


class History:
    """
    History class is a circular array of game results with a fixed size.
    """
    def __init__(self, size):
        self.size = size
        self._history = [None] * size
        self._index = 0
        
    def append(self, game_result):
        self._history[self._index] = game_result
        self._index = (self._index + 1) % self.size
        
    def first(self):
        return self._history[self._index]
    
    def last(self):
        return self._history[self._index - 1]
    
    def toArray(self):
        return self._history[self._index:] + self._history[:self._index]

class Engine(EventEmitter):
  def __init__(self, ):
    super().__init__()
    self._userInfo = UserInfo('test', 100000, 0, 0, [])
    self.stopping = False
    self.gameState = "GAME_STARTING"
    self.history = History(50)


  def getCurrentBet(self):
    if not self.next:
      return None
    return {'wager': self.next['wager'], 'payout': self.next['payout']}

  def getState(self):
    return {
      'userInfo': self._userInfo,
      'history': self.history.toArray(),
      'currentBet': self.getCurrentBet(),
      'isBetQueued': self.isBetQueued()
    }

  def isBetQueued(self):
    return bool(self.next)

  def cancelQueuedBet(self):    
    self.next = None

  def bet(self, wager, payout):
    if self.stopping or self.next:
      return None
    else:
      self.next = {'wager': wager, 'payout': round(payout * 100) / 100, 'isAuto': False}
            
  def cashOut(self):
    pass
    