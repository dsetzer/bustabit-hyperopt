import asyncio
import logging
from collections import deque
import STPyV8

logging.basicConfig(level=logging.DEBUG)

class UserInfo:
    def __init__(self, username, balance):
        self.uname = username
        self.balance = balance
        self.wagers = 0
        self.wagered = 0
        self.profit = 0

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


class Engine(STPyV8.JSClass):
    def __init__(self, user_info):
        self._callback_event = asyncio.Event()
        self._callback_counter = 0
        self._event_callbacks = {
            "GAME_STARTING": [],
            "GAME_STARTED": [],
            "GAME_ENDED": [],
            "BET_PLACED": [],
            "CASHED_OUT": []
        }
        self._userInfo = user_info
        self._pendingBet = None
        self.gameState = "GAME_STARTING"
        self.history = History(50)
        self.gameId = 1
        self.hash = None
        self.bust = None
        self.wager = None
        self.payout = None
        self.cashedAt = None

    def on(self, event, callback):
        def wrapped_callback(*args):
            callback(*args)
            self._done()
        self._event_callbacks[event].append(wrapped_callback)

    def off(self, event, callback):
        self._event_callbacks[event].remove(callback)

    def bet(self, wager, payout):
        if self._pendingBet is not None:
            raise ValueError("A bet is already placed.")
        if wager % 100 != 0:
            raise ValueError("The wager must be a multiple of 100.")
        if self._userInfo.balance < wager:
            raise ValueError("Insufficient balance to place bet.")
        if payout <= 1:
            raise ValueError("Payout must be 1.01x or greater.")
        self._pendingBet = {'wager': wager, 'payout': round(payout * 100) / 100}

    def isBetQueued(self):
        return self._pendingBet is not None

    def cancelQueuedBet(self):
        if self.isBetQueued():
            self._pendingBet = None

    def getState(self):
        return {
            'gameState': self.gameState,
            'gameId': self.gameId, 'hash': self.hash, 'bust': self.bust,
            'wager': self.wager, 'payout': self.payout, 'cashedAt': self.cashedAt,
            'playing': {}, 'cashOuts': [],
        }

    def getCurrentBet(self):
        if self.wager and self.payout:
            return {'wager': self.wager, 'payout': self.payout}
        return None

    def cashOut(self):
        pass

    async def _emit(self, event, *args):
        self._callback_counter += len(self._event_callbacks[event])
        if self._callback_counter > 0:
            self._callback_event.clear()
        for callback in self._event_callbacks[event]:
            callback(*args)
        if self._callback_counter > 0:
            await self._wait_for_callbacks()

    async def _nextGame(self, gameResult):
        self.gameId = gameResult['id']
        # Reset the game variables
        self.hash = self.bust = self.wager = self.payout = self.cashedAt = None
        
        # Emit the game starting event
        self.gameState = "GAME_STARTING"
        await self._emit('GAME_STARTING')

        # If there is a pending bet, place it
        if self._pendingBet:
            self.wager = self._pendingBet['wager']
            self.payout = self._pendingBet['payout']
            self._pendingBet = None
            self._userInfo.balance -= self.wager
            self._userInfo.wagers += 1
            self._userInfo.wagered += self.wager
            await self._emit('BET_PLACED', {'uname': self._userInfo.uname, 'wager': self.wager, 'payout': self.payout })

        # Emit the game started event
        self.gameState = "GAME_IN_PROGRESS"
        await self._emit('GAME_STARTED')

        # Update the game variables with the game result
        self.bust = gameResult['bust']
        self.hash = gameResult['hash']

        # If a bet was placed check if it was a winner
        if self.wager is not None and self.payout <= self.bust:
            self.cashedAt = self.payout
            self._userInfo.balance += (self.wager * self.payout)
            self._userInfo.profit += (self.wager * (self.payout - 1))
            await self._emit('CASHED_OUT', {'uname': self._userInfo.uname, 'wager': self.wager, 'cashedAt': self.cashedAt })

        # Append the game to the history
        self.history.append({
            'id': self.gameId,
            'hash': self.hash,
            'bust': self.bust,
            'wager': self.wager, 
            'payout': self.payout,
            'cashedAt': self.cashedAt
        })
        
        # Emit the game ended event
        self.gameState = "GAME_ENDED"
        await self._emit('GAME_ENDED')
        

    def _done(self):
        self._callback_counter -= 1
        if self._callback_counter == 0:
            self._callback_event.set()

    async def _wait_for_callbacks(self):
        self._callback_event.set()
        while self._callback_event.is_set():
            await asyncio.sleep(0.1)