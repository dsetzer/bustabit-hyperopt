import asyncio
import unittest
from simulator import Simulator, GameResults
from script import Script

class TestSimulator(unittest.TestCase):
    def setUp(self):
        self.script = Script('scripts/example.js')
        self.simulator = Simulator(self.script)
        self.game_results = GameResults(1.98, 3, 100)

    def test_run_single_simulation(self):
        initial_balance = 1000000
        set_index = 0
        result = asyncio.run(self.simulator.run_single_simulation(initial_balance, self.game_results, set_index))
        self.assertIsNotNone(result[0])
        self.assertIsNotNone(result[1])

    def test_run(self):
        initial_balance = 1000000
        result = asyncio.run(self.simulator.run(initial_balance, self.game_results))
        self.assertIsNotNone(result["config"])
        self.assertIsNotNone(result["results"])
        self.assertIsNotNone(result["output"])
        print(result["config"])
        print(result["results"])
        print(result["output"])
        
simulator = TestSimulator()
simulator.setUp()
# simulator.test_run_single_simulation()
simulator.test_run()
