import asyncio
import gc
import logging
import math
import time
import numpy as np
import random
import tracemalloc
from math import exp, log
from simulator import Simulator
from storage import Storage

class Particle:
    def __init__(self, position, velocity):
        self.position = np.array(list(position.values()))
        self.velocity = np.array(list(velocity.values()))
        self.pbest_position = self.position.copy()
        self.pbest_value = float('inf')
        self.id = id(self)  # Add an id attribute

    def __repr__(self):
        return f"Particle(Position: {self.position}, Velocity: {self.velocity}, PBest: {self.pbest_position}, PBest Value: {self.pbest_value})"

class PSOptimizer:
    def __init__(self, script_obj, initial_balance, game_results, parameter_names, space, optimization_id=None):
        self.script_obj = script_obj
        self.initial_balance = initial_balance
        self.game_results = game_results
        self.parameter_names = parameter_names
        self.space = space

        self.num_particles = 10
        self.max_iter = 100
        self.c1 = 1.5
        self.c2 = 1.5
        self.w = 0.9
        self.damping = 0.5


        self.simulator = Simulator(self.script_obj)

        self.storage = Storage('optimizations.db')
        self.optimization_id = optimization_id or self.generate_optimization_id()
        self.current_iteration = 0

        # Initialize global best
        self.gbest_position = np.zeros(len(self.parameter_names))
        self.gbest_value = float('inf')
        self.load_or_initialize_optimization()

    def generate_optimization_id(self):
        while True:
            optimization_id = f"opt_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            if not self.storage.optimization_exists(optimization_id):
                return optimization_id

    def initialize_optimization(self):
        self.current_iteration = 0
        self.gbest_value = float('inf')
        self.gbest_position = {key: 0.0 for key in self.parameter_names}
        self.initialize_particles()

    def load_or_initialize_optimization(self):
        if self.optimization_id:
            loaded_state = self.storage.load_optimization(self.optimization_id)
            if loaded_state:
                self.load_optimization_state(loaded_state)
            else:
                self.initialize_optimization()
        else:
            self.initialize_optimization()

    def load_optimization_state(self, state):
        self.num_particles = state['num_particles']
        self.max_iter = state['max_iter']
        self.c1 = state['c1']
        self.c2 = state['c2']
        self.w = state['w']
        self.damping = state['damping']
        self.gbest_value = state['gbest_value']
        self.gbest_position = np.array(state['gbest_position'])
        self.current_iteration = state['current_iteration']

        # Load particles from the latest iteration state
        latest_iteration = self.storage.load_iteration_state(self.optimization_id, self.current_iteration)
        if latest_iteration:
            self.particles = [
                Particle(
                    position=np.array(particle_data['position']),
                    velocity=np.array(particle_data['velocity'])
                ) for particle_data in latest_iteration['particles']
            ]
            for particle, particle_data in zip(self.particles, latest_iteration['particles']):
                particle.pbest_position = np.array(particle_data['pbest_position'])
                particle.pbest_value = particle_data['pbest_value']

            self.gbest_position = np.array(latest_iteration['gbest_position'])
            self.gbest_value = latest_iteration['gbest_value']
        else:
            self.initialize_particles()

    def save_optimization_state(self):
        optimization_data = {
            "optimization_id": self.optimization_id,
            "script_obj": self.script_obj,
            "initial_balance": self.initial_balance,
            "num_particles": self.num_particles,
            "max_iter": self.max_iter,
            "c1": self.c1,
            "c2": self.c2,
            "w": self.w,
            "damping": self.damping,
            "gbest_value": float(self.gbest_value),
            "gbest_position": self.gbest_position.tolist(),
            "status": "in_progress",
            "current_iteration": self.current_iteration
        }
        if self.storage.optimization_exists(self.optimization_id):
            self.storage.update_optimization(self.optimization_id, optimization_data)
        else:
            self.storage.save_optimization(optimization_data)

        iteration_data = {
            "iteration": self.current_iteration,
            "particles": [
                {
                    "position": particle.position.tolist(),
                    "velocity": particle.velocity.tolist(),
                    "pbest_position": particle.pbest_position.tolist(),
                    "pbest_value": float(particle.pbest_value)
                } for particle in self.particles
            ],
            "gbest_position": self.gbest_position.tolist(),
            "gbest_value": float(self.gbest_value)
        }
        self.storage.save_iteration_state(self.optimization_id, iteration_data)

    def initialize_particles(self):
        self.particles = []
        for _ in range(self.num_particles):
            position = np.array([self.sample_from_space(param_name) for param_name in self.parameter_names])
            velocity = np.random.uniform(-1, 1, len(self.parameter_names))
            particle = Particle(dict(zip(self.parameter_names, position)), dict(zip(self.parameter_names, velocity)))
            self.particles.append(particle)

        # Initialize global best
        self.gbest_position = np.zeros(len(self.parameter_names))
        self.gbest_value = float('inf')

        logging.info(f"Initialized {self.num_particles} particles")
        logging.info(f"Initial global best position: {self.gbest_position}")
        logging.info(f"Initial global best value: {self.gbest_value}")

    def sample_from_space(self, param_name):
        param_details = self.space.get(param_name, {})
        param_type = param_details.get('type')
        param_range = param_details.get('range')

        if param_type == 'balance':
            return round(random.uniform(param_range[0], param_range[1]) / 100) * 100
        elif param_type == 'number':
            if param_details.get('is_integer'):
                return round(random.uniform(param_range[0], param_range[1]))
            else:
                return random.uniform(param_range[0], param_range[1])
        elif param_type == 'multiplier':
            u = np.random.random()
            min_val, max_val = param_range
            normalization = 0.99 * log(max_val) - 0.99 * log(min_val)
            return exp(u * normalization + 0.99 * log(min_val))
        elif param_type == 'checkbox':
            return bool(random.getrandbits(1))
        elif param_type == 'radio':
            return random.choice(param_range)
        else:
            raise ValueError(f"Unknown parameter type: {param_type}")

    async def evaluate_fitness(self, particle_position):
        try:
            decoded_particle = self.enforce_constraints(particle)
            sim_result = await self.simulator.run(self.initial_balance, self.game_results, decoded_particle)
            if sim_result[1] == "SCRIPT_ERROR":
                fitness = float('inf')
            elif sim_result[1] == "INSUFFICIENT_BALANCE":
                fitness = float('inf')
            else:
                fitness = sim_result[0].get_metric()
        except Exception as e:
            logging.error(f"Error evaluating fitness for particle: {e}")
            fitness = float('inf')
        return fitness

    def enforce_constraint(self, param_name, value):
        param_details = self.space.get(param_name, {})
        param_type = param_details.get('type')
        param_range = param_details.get('range')

        if param_type == 'balance':
            return max(min(round(value / 100) * 100, param_range[1]), param_range[0])
        elif param_type == 'number':
            if param_details.get('is_integer'):
                return round(max(min(value, param_range[1]), param_range[0]))
            else:
                return max(min(value, param_range[1]), param_range[0])
        elif param_type == 'multiplier':
            return max(min(value, param_range[1]), param_range[0])
        elif param_type == 'checkbox':
            return bool(round(value))
        elif param_type == 'radio':
            return param_range[0]  # Always return the first option for radio
        else:
            raise ValueError(f"Unknown parameter type: {param_type}")

    def enforce_constraints(self, particle_position):
        constrained_position = np.zeros_like(particle_position)
        for i, (param_name, value) in enumerate(zip(self.parameter_names, particle_position)):
            constrained_position[i] = self.enforce_constraint(param_name, value)
        return constrained_position

    async def update_particles(self):
        for particle in self.particles:
            # Calculate the inertia component
            inertia = self.w * particle.velocity

            # Calculate the cognitive component
            cognitive = self.c1 * np.random.random((len(particle.position),)) * (particle.pbest_position - particle.position)

            # Calculate the social component
            social = self.c2 * np.random.random((len(particle.position),)) * (self.gbest_position - particle.position)

            # Update the velocity of the particle
            particle.velocity = inertia + cognitive + social

            # Update the position of the particle and enforce constraints
            try:
                particle.position += particle.velocity
                particle.position = self.enforce_constraints(particle.position)
            except Exception as e:
                logging.error(f"Error enforcing constraints for particle {particle.id}: {str(e)}")
                continue

            # Evaluate the fitness of the particle
            try:
                fitness = await self.evaluate_fitness(particle.position)
            except Exception as e:
                logging.error(f"Error evaluating fitness for particle {particle.id}: {str(e)}")
                continue

            logging.info(f"Particle {particle.id} fitness: {fitness}")

            # Update personal and global bests
            if fitness < particle.pbest_value:
                particle.pbest_position = particle.position.copy()
                particle.pbest_value = fitness

            if fitness < self.gbest_value:
                self.gbest_position = particle.position.copy()
                self.gbest_value = fitness
                logging.info(f"New global best found: Position {self.gbest_position}, Value {self.gbest_value}")

        logging.info(f"Current global best fitness: {self.gbest_value}")
        logging.info(f"Current global best position: {self.gbest_position}")

    async def optimize(self):
        # Start memory profiling
        tracemalloc.start()

        # Initialize the particles
        self.initialize_particles()

        # Save the initial state
        self.save_optimization_state()

        # Start the optimization loop
        for iter_num in range(self.current_iteration, self.max_iter):
            self.current_iteration = iter_num
            logging.info(f"Iteration {iter_num + 1}")
            await self.update_particles()
            self.save_optimization_state()

            if iter_num == 0:
                snapshot0 = tracemalloc.take_snapshot()
            else:
                snapshot1 = tracemalloc.take_snapshot()
                top_stats = snapshot1.compare_to(snapshot0, 'lineno')
                print("[ Top 10 differences ]")
                for stat in top_stats[:10]:
                    print(stat)
                snapshot0 = snapshot1

            gc.collect()

        # print a final snapshot
        snapshot1 = tracemalloc.take_snapshot()
        top_stats = snapshot1.compare_to(snapshot0, 'lineno')
        print("[ Top 10 differences ]")
        for stat in top_stats[:10]:
            print(stat)

        tracemalloc.stop()
        self.save_final_result()
        logging.info(f"Optimization completed. Best position: {dict(zip(self.parameter_names, self.gbest_position))}, Best value: {self.gbest_value}")

        return {'best_parameters': self.gbest_position.tolist(), 'best_metric': self.gbest_value}

    def save_final_result(self):
        final_state = {
            "optimization_id": self.optimization_id,
            "script_obj": self.script_obj,
            "initial_balance": self.initial_balance,
            "num_particles": self.num_particles,
            "max_iter": self.max_iter,
            "c1": self.c1,
            "c2": self.c2,
            "w": self.w,
            "damping": self.damping,
            "gbest_value": self.gbest_value,
            "gbest_position": self.gbest_position.tolist(),
            "status": "completed",
            "current_iteration": self.current_iteration
        }
        self.storage.update_optimization(self.optimization_id, final_state)

