import asyncio
import binascii
import hashlib
import hmac
import math
import random
from statistics import median
from typing import List, Dict, Any, Tuple
from py_mini_racer import py_mini_racer

import pythonmonkey as pm
from engine import Engine, UserInfo
from metrics import Statistics
from script import Script

class GameResults:
    def __init__(self, required_median: float, num_sets: int, num_games: int):
        """
        :param required_median: The median bust value the generated results should have
        :param num_sets: The number of sets of results to generate
        :param num_games: The number of games in each set of results
        :return: A list of lists of dictionaries, where each dictionary is a game result
        """
        self.required_median = required_median
        self.num_sets = num_sets
        self.num_games = num_games
        self.result_sets = [self.generate_sim_results() for _ in range(self.num_sets)]

    @staticmethod
    def generate_games(hash_value: str, num_games: int) -> List[Dict[str, Any]]:
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

    def generate_sim_results(self) -> List[Dict[str, Any]]:
        while True:
            game_hash = hashlib.sha256(str(random.random()).encode()).hexdigest()
            generated_results = self.generate_games(game_hash, self.num_games)
            busts = [game['bust'] for game in generated_results]
            if round(median(busts), 2) == self.required_median:
                return generated_results

class Simulator:
    def __init__(self, script: Script):
        """
        Initializes a Simulator object
        
        :param script: The script to run
        """
        self.script = script
        self.shouldStop = False
        self.shouldStopReason = None
        self.ctx = py_mini_racer.MiniRacer()

    async def run_single_simulation(self, initial_balance: float, game_set: List[Dict[str, Any]], script_params: Dict[str, Any]) -> Tuple[Statistics, Any]:
        user_info = UserInfo("Player", initial_balance)
        engine = Engine(user_info)
        statistics = Statistics(initial_balance)

        def stop(reason: str):
            self.shouldStop = True
            engine.stopping = True
            if engine.next is not None:
                engine.next = None

        # Create a new context for each simulation
        self.ctx = py_mini_racer.MiniRacer()
        
        # Set up the globals directly in the context
        self.ctx.eval("""
            var engine = arguments[0];
            var userInfo = arguments[1];
            var stop = arguments[2];
            var log = arguments[3];
            var SHA256 = arguments[4];
            var gameResultFromHash = arguments[5];
        """)

        globals_dict = [
            engine,
            user_info,
            stop,
            lambda *msgs: None,  # Discard log messages
            lambda x: hashlib.sha256(x.encode()).hexdigest(),
            lambda game_hash: GameResults.generate_games(game_hash, 1)[0],
        ]

        try:
            # Evaluate the script directly
            self.ctx.eval(self.script.merge_config())
            self.ctx.call("eval", self.script.js_code, *globals_dict)
        except Exception as e:
            return ("SCRIPT_ERROR", None, f"SCRIPT_ERROR: {str(e)}")

        try:
            for game in game_set:
                await engine._nextGame(game)
                statistics.update(engine)
                if self.shouldStop:
                    break
                if statistics.balance <= 0:
                    return ("INSUFFICIENT_BALANCE", None, "INSUFFICIENT_BALANCE")
        except Exception as e:
            return ("SIMULATION_ERROR", None, f"SIMULATION_ERROR: {str(e)}")

        return ("OK", statistics)

    async def run(self, initial_balance: float, game_results: GameResults, script_params: Dict[str, Any]) -> Tuple[str, Any]:
        """Runs multiple simulations and aggregates the results.

        Args:
            initial_balance: The initial balance to use for each simulation.
            game_results: The game results to use for each simulation.
            script_params: The script parameters to set for the script.

        Returns:
            A tuple containing the result of the simulation and the aggregated statistics.
        """
        try:
            self.shouldStop = False
            self.shouldStopReason = None
            # Run multiple simulations in parallel
            tasks = [self.run_single_simulation(initial_balance, game_set, script_params) for game_set in game_results.result_sets]
            results = await asyncio.gather(*tasks)

            # Filter out invalid results
            valid_results = [result for result in results if result[0] != "SCRIPT_ERROR" and result[0] != "INSUFFICIENT_BALANCE"]

            # If there are no valid results, return an error
            if len(valid_results) == 0:
                if any([result[0] == "SCRIPT_ERROR" for result in results]):
                    return ("SCRIPT_ERROR", None)
                else:
                    return ("INSUFFICIENT_BALANCE", None)

            # Aggregate the statistics of the valid results
            aggregated_statistics = [result[1] for result in valid_results if result[1].balance != 0]

            # If there are no valid results with a balance, return an error
            if not aggregated_statistics:
                return ("INSUFFICIENT_BALANCE", None)

            # Calculate the average of the aggregated statistics
            averaged_statistics = Statistics.average_statistics(aggregated_statistics)

            # Return the result and the averaged statistics
            return ("OK", averaged_statistics)
        except Exception as e:
            # Catch any exceptions and return an error
            return ("SIMULATION_ERROR", None)
