import STPyV8
from engine import Engine, UserInfo, History
from script import Script
from statistics import Statistics
import hashlib
import hmac
import binascii
import math
from collections import deque
from pyee import EventEmitter
import math  # Import for math.log


class Simulator:
    def __init__(self, script):
        self.js_context = None
        self.script = script
        
        self.discard_logs = True
        self.logMessages = []
        
        self.engine = None
        self.userInfo = None
        
        self.shouldStop = False
        self.shouldStopReason = None
        
        self.statistics = None

    def log(self, *msgs):
        if self.discard_logs:
            return
        else:
            msg = " ".join(msgs)
            self.logMessages.append('LOG: '+msg)
            print("LOG:", msgs)
    
    def stop(self, reason):
        self.shouldStop = True
        self.engine.stopping = True
        if self.engine.next != None:
            self.engine.next = None;
        print("Simulation stopped:", reason)
    
    def gameResultFromHash(self, hash_value):
        return self.generate_games(hash_value, 1)[0]['result']
    
    def SHA256(self, text):
        return hashlib.sha256(text.encode()).hexdigest()
    
    def run(self, initial_balance, game_hash, num_games, discard_logs=True):
        self.shouldStop = False
        self.shouldStopReason = None
        self.discard_logs = discard_logs
        self.logMessages = []

        self.engine = Engine()
        self.userInfo = UserInfo("Player", initial_balance)
        self.engine._userInfo = self.userInfo
        
        self.statistics = Statistics(initial_balance)
        
        self.hash_value = game_hash
        self.num_games = num_games
        self.game_results = self.generate_games(self.hash_value, self.num_games)
        
        with STPyV8.JSContext() as self.js_context:
            try:
                self.js_context.locals.engine = self.engine
                self.js_context.locals.userInfo = self.userInfo
                self.js_context.locals.stop = self.stop
                self.js_context.locals.log = self.log
                self.js_context.locals.gameResultFromHash = self.gameResultFromHash
                self.js_context.locals.SHA256 = self.SHA256
        
                self.js_context.eval(self.script.get_combined_js_code())
                    
                # Iterate through the games
                for i, game in enumerate(self.game_results):
                    # Emit GAME_STARTING event and run the script
                    self.engine._gameStarting()
                    
                    # Emit GAME_STARTED event
                    self.engine._gameStarted()
                    
                    # Emit GAME_ENDED event and update history
                    self.engine._gameEnded(game["result"], game["hash"])

                    # Update the statistics
                    self.statistics.update(self.engine)
                    
                    # Check for stopping condition
                    if self.shouldStop:
                        break

            except STPyV8.JSError as e:
                print(f"A JavaScript error occurred: {e}")

            # Print the statistics at the end
            print(self.statistics)
            
            # Return the ending balance
            return self.userInfo.balance


    def generate_games(self, hash_value, num_games):
        salt = '0000000000000000004d6ec16dafe9d8370958664c1dc422f452892264c59526'.encode()
        hashobj = hmac.new(salt, binascii.unhexlify(hash_value), hashlib.sha256)

        game_results = []
        for i in range(num_games):
            number = 0
            intversion = int(hashobj.hexdigest()[0:int(52/4)], 16)
            number = max(1, math.floor(100 / (1 - (intversion / (2 ** 52)))) / 101)
            game_results.append({'hash': hash_value, 'result': number})
            hash_value = hashlib.sha256(hash_value.encode()).hexdigest()
            hashobj = hmac.new(salt, binascii.unhexlify(hash_value), hashlib.sha256)

        return game_results