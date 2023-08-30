import STPyV8
from pyee import EventEmitter
from collections import deque


class UserInfo:
    def __init__(self, uname, balance, wagered=0, profit=0, bets=0):
        self.uname = uname
        self.balance = balance
        self.wagered = wagered
        self.profit = profit
        self.bets = bets

    def __str__(self):
        return f"UserInfo(uname={self.uname}, balance={self.balance}, wagered={self.wagered}, profit={self.profit}, bets={self.bets})"


class History:
    def __init__(self, size=50):
        self.buffer = deque(maxlen=size)

    def first(self):
        return self.buffer[0] if self.buffer else None

    def last(self):
        return self.buffer[-1] if self.buffer else None

    def toArray(self):
        return list(self.buffer)

    def size(self):
        return len(self.buffer)


class Engine(EventEmitter, STPyV8.JSClass):
    def __init__(self, ):
        super().__init__()
        self._userInfo = UserInfo('Player', 100000)
        self.stopping = False
        self.gameState = "GAME_STARTING"
        self.history = History(50)
        self.next = None
        self.gameId = 0
        self.bust = 0
        self.wager = None
        self.payout = None
        self.cashedAt = None
        self.hash = None

    def _gameStarting(self):
        self.gameId += 1
        self.bust = 0
        self.cashedAt = None
        self.hash = None

        self.gameState = "GAME_STARTING"
        self.emit('GAME_STARTING')
        if self.next:
            self.wager = self.next['wager']
            self.payout = self.next['payout']
            self.next = None
            self.emit('BET_PLACED', {'wager': self.wager, 'payout': self.payout, 'uname': self._userInfo.uname})

    def _gameStarted(self):
        self.gameState = "GAME_STARTED"
        self.emit('GAME_STARTED')

        if self.wager is not None and self.payout <= self.bust:
            self.cashedAt = self.payout
            winnings = self.wager * self.payout
            self._userInfo.balance += winnings
            self.emit('CASHED_OUT', {'wager': self.wager, 'cashedAt': self.cashedAt, 'uname': self._userInfo.uname})
            self.wager = None
            self.payout = None

    def _gameEnded(self, bust, hash):
        self.gameState = "GAME_ENDED"
        self.bust = bust
        self.hash = hash
        self.history.buffer.append({
            'gameId': self.gameId,
            'wager': self.wager,
            'payout': self.payout,
            'cashedAt': self.cashedAt,
            'bust': self.bust,
            'hash': self.hash
        })
        self.emit('GAME_ENDED')

    def getState(self):
        return {
            'userInfo': self._userInfo,
            'history': self.history.toArray(),
            'currentBet': self.getCurrentBet(),
            'isBetQueued': self.isBetQueued()
        }
        
    def getCurrentBet(self):
        if not self.wager or not self.payout:
            return None
        return {'wager': self.wager, 'payout': self.payout}

    def isBetQueued(self):
        return bool(self.next)

    def cancelQueuedBet(self):
        self.next = None

    def bet(self, wager, payout):
        if self.gameState == "GAME_STARTING":
            # already placed a bet for this round
            if self.wager is None:
                self.wager = wager
                self.payout = payout
                self.emit('BET_PLACED', {'wager': self.wager, 'payout': self.payout, 'uname': self._userInfo.uname})

        elif not self.stopping and not self.next:
            # queue the bet for the next round
            self.next = {'wager': wager, 'payout': round(payout * 100) / 100}

    def cashOut(self):
        pass