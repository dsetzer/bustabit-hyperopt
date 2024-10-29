import unittest
from unittest.mock import patch, MagicMock
from ps_optimizer import PSOptimizer, Particle
from simulator import Simulator, GameResults
from script import Script
from storage import Storage

class TestPSOptimizer(unittest.TestCase):
    def setUp(self):
        self.script = Script('scripts/example.js')
        self.initial_balance = 1000000
        self.game_results = GameResults(1.98, 3, 100)
        self.parameter_names = ['baseBet', 'payout', 'waitNum']
        self.space = {
            'baseBet': {'range': (100, 1000), 'type': 'balance'},
            'payout': {'range': (1.01, 10), 'type': 'payout'},
            'waitNum': {'range': (1, 10), 'type': 'number'}
        }
        self.optimizer = PSOptimizer(self.script, self.initial_balance, self.game_results, self.parameter_names, self.space)

    def test_initialize_particles(self):
        self.optimizer.initialize_particles()
        self.assertEqual(len(self.optimizer.particles), self.optimizer.num_particles)
        for particle in self.optimizer.particles:
            self.assertIn('baseBet', particle.position)
            self.assertIn('payout', particle.position)
            self.assertIn('waitNum', particle.position)

    @patch('ps_optimizer.Simulator.run', return_value=MagicMock())
    def test_evaluate_fitness(self, mock_run):
        particle = Particle({'baseBet': 100, 'payout': 2, 'waitNum': 3}, {'baseBet': 0, 'payout': 0, 'waitNum': 0})
        mock_run.return_value = {'results': MagicMock(get_metric=lambda: 1.0)}
        fitness = self.optimizer.evaluate_fitness(particle.position)
        self.assertEqual(fitness, 1.0)

    @patch('ps_optimizer.Simulator.run', return_value=MagicMock())
    def test_update_particles(self, mock_run):
        self.optimizer.initialize_particles()
        mock_run.return_value = {'results': MagicMock(get_metric=lambda: 1.0)}
        self.optimizer.update_particles()
        for particle in self.optimizer.particles:
            self.assertIsNotNone(particle.pbest_position)
            self.assertIsNotNone(particle.pbest_value)

    @patch('ps_optimizer.Simulator.run', return_value=MagicMock())
    def test_optimize(self, mock_run):
        self.optimizer.initialize_particles()
        mock_run.return_value = {'results': MagicMock(get_metric=lambda: 1.0)}
        result = self.optimizer.optimize()
        self.assertIsNotNone(result['best_parameters'])
        self.assertIsNotNone(result['best_metric'])

if __name__ == '__main__':
    unittest.main()
