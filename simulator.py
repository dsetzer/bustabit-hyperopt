import asyncio
import binascii
import hashlib
import hmac
import math
import random
from statistics import median

import pythonmonkey as pm
from engine import Engine, UserInfo
from metrics import Statistics
from script import Script


class GameResults:
    def __init__(self, required_median: float, num_sets: int, num_games: int):
        self.required_median = required_median
        self.num_sets = num_sets
        self.num_games = num_games
        self.result_sets = [self.generate_sim_results() for _ in range(self.num_sets)]

    @staticmethod
    def generate_games(hash_value, num_games):
        salt = '0000000000000000004d6ec16dafe9d8370958664c1dc422f452892264c59526'.encode()
        hashobj = hmac.new(salt, binascii.unhexlify(hash_value), hashlib.sha256)
        game_results = []
        for i in range(num_games):
            intversion = int(hashobj.hexdigest()[: 52 // 4], 16)
            number = max(1, math.floor(100 / (1 - intversion / 2**52)) / 101)
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
        self.script = Script(script)
        self.shouldStop = False
        self.shouldStopReason = None

    async def run_single_simulation(self, initial_balance, game_set, script_params):
        userInfo = UserInfo("Player", initial_balance)
        engine = Engine(userInfo)
        statistics = Statistics(initial_balance)

        def stop(reason):
            self.shouldStop = True
            engine.stopping = True
            if engine.next is not None:
                engine.next = None

        def SHA256(text: str):
            return hashlib.sha256(text.encode()).hexdigest()

        def gameResultFromHash(game_hash: str):
            return GameResults.generate_games(game_hash, 1)[0]

        # Set JavaScript variables
        pm.globalThis.engine = engine
        pm.globalThis.userInfo = userInfo
        pm.globalThis.stop = stop
        pm.globalThis.log = lambda *msgs: None  # Discard log messages
        pm.globalThis.SHA256 = SHA256
        pm.globalThis.gameResultFromHash = gameResultFromHash

        # Evaluate the script with the merged config
        self.script.evaluate(globals_dict)

        try:
            for game in game_set:
                await engine._nextGame(game)
                statistics.update(engine)
                if self.shouldStop:
                    break
        except ValueError as e:  # Catch the insufficient balance error
            return ( Statistics(0), None, )  # Return a Statistics object with a very low balance to indicate failure

        return statistics, None

    async def run(self, initial_balance, game_results, script_params):
        try:
            self.shouldStop = False
            self.shouldStopReason = None
            tasks = [ self.run_single_simulation(initial_balance, game_set, script_params) for game_set in game_results.result_sets ]
            results = await asyncio.gather(*tasks)

            if any(result[0] == "SCRIPT_ERROR" for result in results):
                raise Exception("Script error detected. Discarding all simulations.")

            if any(result[0] == "INSUFFICIENT_BALANCE" for result in results):
                raise Exception("Insufficient balance detected. Discarding all simulations.")

            aggregated_statistics = [result[0] for result in results if result[0].balance != 0]

            if not aggregated_statistics:
                raise Exception( "All simulations returned None or an empty list. No average statistics available." )

            averaged_statistics = Statistics.average_statistics(aggregated_statistics)

            return averaged_statistics, None
        except Exception as e:
            raise e