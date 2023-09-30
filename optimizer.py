import numpy as np
import asyncio
import logging
from functools import partial
from skopt import gp_minimize
from skopt.space import Categorical, Integer, Real, Space
from skopt.callbacks import DeltaYStopper
from script import Script
from simulator import GameResults, Simulator

class Optimizer:
    def __init__(self, script_obj: Script, initial_balance: int, game_results: GameResults, parameter_names: list, space: Space):
        self.script_obj = script_obj
        self.initial_balance = initial_balance
        self.game_results = game_results
        self.parameter_names = parameter_names
        self.space = space

    def estimate_noise_at_point(self, run_single_simulation, point, N=30):
        objective_values = []
        for _ in range(N):
            value = run_single_simulation(point)
            objective_values.append(value)
        return np.std(objective_values)

    def estimate_noise_across_space(self, run_single_simulation, points, N=30):
        noise_estimates = {}
        for point in points:
            noise = self.estimate_noise_at_point(run_single_simulation, point, N)
            noise_estimates[tuple(point)] = noise
        return noise_estimates

    def create_custom_delta_stopper(self, delta, n_best, error_value):
        values = []
        def custom_delta_stopper(result):
            nonlocal values
            if result.fun == error_value:
                return False    
            if len(values) >= n_best:
                values.pop(0)
            values.append(result.fun)
            if len(values) < n_best:
                return False    
            return all(abs(v - values[-1]) <= delta for v in values[:-1])
        return custom_delta_stopper

    def objective(self, params):
        param_dict = dict(zip(self.parameter_names, params))
        self.script_obj.set_params(**param_dict)
        simulator = Simulator(self.script_obj)
        loop = asyncio.get_event_loop()
        try:
            result = loop.run_until_complete(simulator.run(self.initial_balance, self.game_results))
        except Exception as e:
            logging.error(f"Failed to run simulator: {e}")
            return 1e12  
        try:
            averaged_statistics = result["results"]
            metric = averaged_statistics.get_metric()
        except Exception as e:
            logging.error(f"Failed to get metric: {e}")
            return 1e12  
        logging.info(f"Params: {param_dict}, Metric: {metric}")
        return metric

    def run_optimization(self):
        delta_callback = self.create_custom_delta_stopper(delta=1e-4, n_best=10, error_value=1e12)
        res = gp_minimize(
            func=self.objective,
            dimensions=self.space,
            n_calls=1000000000,
            n_initial_points=20,
            acq_func='gp_hedge',
            x0=None,
            y0=None,
            random_state=42,
            verbose=True,
            callback=[delta_callback],
            n_points=5000,
            n_restarts_optimizer=10,
            xi=0.02,
            kappa=1.96,
            noise='gaussian',
            n_jobs=-1
        )
        results_dict = {
            'best_parameters': dict(zip(self.parameter_names, res.x)),
            'best_metric': res.fun,
            'top_10_results': []
        }
        sorted_indices = np.argsort(res.func_vals)
        top_10_indices = sorted_indices[:10]
        for i, index in enumerate(top_10_indices):
            result = {
                'rank': i + 1,
                'parameters': dict(zip(self.parameter_names, res.x_iters[index])),
                'metric': res.func_vals[index]
            }
            results_dict['top_10_results'].append(result)
        return results_dict
