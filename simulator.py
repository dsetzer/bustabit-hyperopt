import binascii
import hashlib
import hmac
import math  # Import for math.log
from collections import deque
from statistics import Statistics
from engine import Engine, History, UserInfo
from script import Script

import STPyV8
from pyee import EventEmitter


def generate_games(hash_value, num_games):
    salt = '0000000000000000004d6ec16dafe9d8370958664c1dc422f452892264c59526'.encode()
    hashobj = hmac.new(salt, binascii.unhexlify(hash_value), hashlib.sha256)

    game_results = []
    for i in range(num_games):
        number = 0
        intversion = int(hashobj.hexdigest()[0:int(52/4)], 16)
        number = max(1, math.floor(100 / (1 - (intversion / (2 ** 52)))) / 101)
        game_results.append({'hash': hash_value, 'bust': number})
        hash_value = hashlib.sha256(hash_value.encode()).hexdigest()
        hashobj = hmac.new(salt, binascii.unhexlify(
            hash_value), hashlib.sha256)

    game_results.reverse()
    return game_results


class Simulator:
    def __init__(self, script):
        self.js_context = None
        self.engine = None
        self.userInfo = None
        self.logMessages = []
        self.script = script

        self.shouldStop = False
        self.shouldStopReason = None

        self.statistics = None

    def log(self, *msgs):
        str_msgs = [str(msg) for msg in msgs]
        msg = " ".join(str_msgs)
        self.logMessages.append('LOG: '+msg)
        print("LOG:", msg)

    def stop(self, reason):
        self.shouldStop = True
        self.engine.stopping = True
        if self.engine.next != None:
            self.engine.next = None
        print("Simulation stopped:", reason)

    def gameResultFromHash(self, hash_value):
        return self.generate_games(hash_value, 1)[0]['result']

    def SHA256(self, text):
        return hashlib.sha256(text.encode()).hexdigest()

    async def run(self, initial_balance, game_hash, num_games, discard_logs=True):
        self.shouldStop = False
        self.shouldStopReason = None
        self.logMessages = []

        self.userInfo = UserInfo("Player", initial_balance)
        self.engine = Engine(self.userInfo)

        self.statistics = Statistics(initial_balance)

        self.hash_value = game_hash
        self.num_games = num_games
        self.game_results = generate_games(self.hash_value, self.num_games)

        with STPyV8.JSContext() as self.js_context:
            try:
                self.js_context.locals.engine = self.engine
                self.js_context.locals.userInfo = self.userInfo
                self.js_context.locals.stop = self.stop
                self.js_context.locals.log = self.log
                self.js_context.locals.gameResultFromHash = self.gameResultFromHash
                self.js_context.locals.SHA256 = self.SHA256
                self.js_context.locals.config = self.script.config_dict

                self.js_context.eval(self.script.js_code)

                # Iterate through the games
                for i, game in enumerate(self.game_results):
                    # Update the engine
                    await self.engine._nextGame({"id": i+1, "hash": game['hash'], "bust": game['bust']})

                    # Update the statistics
                    self.statistics.update(self.engine)

                    # Check for stopping condition
                    if self.shouldStop:
                        break

            except STPyV8.JSError as e:
                print(f"A JavaScript error occurred: {e}")

            # Print the statistics at the end
            print(self.statistics)

            # Return an object containing the script config, the statistics, and the log messages
            return {
                "config": self.script.config_dict,
                "results": self.statistics,
                "output": self.logMessages
            }
