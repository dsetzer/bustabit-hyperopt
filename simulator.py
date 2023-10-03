import binascii
import hashlib
import hmac
import math
import random
from metrics import Statistics
from statistics import median
from engine import Engine, History, UserInfo
from script import Script
import STPyV8
import asyncio

class GameResults:
    def __init__(self, required_median: float, num_sets: int, num_games: int):
        self.required_median = required_median
        self.num_sets = num_sets
        self.num_games = num_games
        self.result_sets = [self.generate_sim_results() for _ in range(self.num_sets)]

    def generate_games(self, hash_value, num_games):
        salt = '0000000000000000004d6ec16dafe9d8370958664c1dc422f452892264c59526'.encode()
        hashobj = hmac.new(salt, binascii.unhexlify(hash_value), hashlib.sha256)
        game_results = []
        for i in range(num_games):
            intversion = int(hashobj.hexdigest()[:52 // 4], 16)
            number = max(1, math.floor(100 / (1 - (intversion / (2 ** 52)))) / 101)
            game_results.append({'id': i + 1, 'hash': hash_value, 'bust': round(number, 2)})
            hash_value = hashlib.sha256(hash_value.encode()).hexdigest()
            hashobj = hmac.new(salt, binascii.unhexlify(hash_value), hashlib.sha256)
        return game_results[::-1]

    def generate_sim_results(self):
        while True:
            game_hash = hashlib.sha256(str(random.random()).encode()).hexdigest()
            generated_results = self.generate_games(game_hash, self.num_games)
            busts = [game['bust'] for game in generated_results]
            median_bust = median(busts)
            if round(median_bust, 2) == self.required_median:
                return generated_results

  
class Simulator:
    def __init__(self, script: Script):
        self.script = script
        self.shouldStop = False
        self.shouldStopReason = None
        
    async def run_single_simulation(self, initial_balance, game_set):
        logMessages = []
        userInfo = UserInfo("Player", initial_balance)
        engine = Engine(userInfo)
        statistics = Statistics(initial_balance)

        def log(*msgs):
            msg = " ".join(map(str, msgs))
            # print(f"LOG: {msg}")
            logMessages.append(f'LOG: {msg}')

        def stop(reason):
            self.shouldStop = True
            engine.stopping = True
            if engine.next != None:
                engine.next = None
            print("Script stopped:", reason)

        def SHA256(text: str):
            return hashlib.sha256(text.encode()).hexdigest()

        def gameResultFromHash(game_hash: str):
            return GameResults.generate_games(game_hash, 1)[0]

        with STPyV8.JSContext() as js_context:
            js_context.locals.engine = engine
            js_context.locals.userInfo = userInfo
            js_context.locals.stop = stop
            js_context.locals.log = log
            js_context.locals.SHA256 = SHA256
            js_context.locals.gameResultFromHash = gameResultFromHash
            js_context.locals.config = self.script.config
            js_context.eval(self.script.js_code)

            try:
                for game in game_set:
                    await engine._nextGame(game)
                    statistics.update(engine)
                    if self.shouldStop:
                        break
            except ValueError as e:  # Catch the insufficient balance error
                return "INSUFFICIENT_BALANCE", logMessages  # Return a special flag to indicate failure

            return statistics, logMessages


    async def run(self, initial_balance, game_results):
        try:
            self.shouldStop = False
            self.shouldStopReason = None
            tasks = [self.run_single_simulation(initial_balance, game_set) for game_set in game_results.result_sets]
            results = await asyncio.gather(*tasks)

            if any(result[0] == "SCRIPT_ERROR" for result in results):
                raise Exception("Script error detected. Discarding all simulations.")

            if any(result[0] == "INSUFFICIENT_BALANCE" for result in results):
                raise Exception("Insufficient balance detected. Discarding all simulations.")

            aggregated_statistics = [result[0] for result in results if result[0] not in ["SCRIPT_ERROR", "INSUFFICIENT_BALANCE"]]
            all_log_messages = [result[1] for result in results if result[1] is not None]

            if not aggregated_statistics:
                raise Exception("All simulations returned None or an empty list. No average statistics available.")

            averaged_statistics = Statistics.average_statistics(aggregated_statistics)

            return {
                "config": self.script.config,
                "results": averaged_statistics,
                "output": all_log_messages
            }
        except Exception as e:
            raise e