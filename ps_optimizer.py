import logging
import time

import numpy as np
import random
from math import exp, log

from simulator import Simulator
from storage import Storage


class Particle:
    def __init__(self, position, velocity):
        self.position = position
        self.velocity = velocity
        self.pbest_position = position
        self.pbest_value = float('inf')

    def __repr__(self):
        return f"Particle(Position: {self.position}, Velocity: {self.velocity}, PBest: {self.pbest_position}, PBest Value: {self.pbest_value})"


class PSOptimizer:
    def __init__(self, script_obj, initial_balance, game_results, parameter_names, space, optimization_id=None):
        self.script_obj = script_obj
        self.initial_balance = initial_balance
        self.game_results = game_results
        self.parameter_names = parameter_names
        self.space = space

        self.num_particles = 30
        self.max_iter = 100
        self.c1 = 1.5
        self.c2 = 1.5
        self.w = 0.9
        self.damping = 0.5

        self.simulator = Simulator(self.script_obj)

        self.storage = Storage('optimizations.db')
        self.optimization_id = optimization_id or self.generate_optimization_id()
        self.current_iteration = 0
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
        self.gbest_position = state['gbest_position']
        self.current_iteration = state['current_iteration']

        # Load particles from the latest iteration state
        latest_iteration = self.storage.load_iteration_state(self.optimization_id, self.current_iteration)
        if latest_iteration:
            self.particles = [
                Particle(
                    position=particle_data['position'],
                    velocity=particle_data['velocity']
                ) for particle_data in latest_iteration['particles']
            ]
            for particle, particle_data in zip(self.particles, latest_iteration['particles']):
                particle.pbest_position = particle_data['pbest_position']
                particle.pbest_value = particle_data['pbest_value']

            self.gbest_position = latest_iteration['gbest_position']
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
            "gbest_value": self.gbest_value,
            "gbest_position": self.gbest_position,
            "status": "in_progress",
            "current_iteration": self.current_iteration
        }
        self.storage.save_optimization(optimization_data)

        iteration_data = {
            "iteration": self.current_iteration,
            "particles": [
                {
                    "position": particle.position,
                    "velocity": particle.velocity,
                    "pbest_position": particle.pbest_position,
                    "pbest_value": particle.pbest_value
                } for particle in self.particles
            ],
            "gbest_position": self.gbest_position,
            "gbest_value": self.gbest_value
        }
        self.storage.save_iteration_state(self.optimization_id, iteration_data)

    def initialize_particles(self):
        self.particles = []

        for _ in range(self.num_particles):
            # Initialize particle with sampled values
            position = {}
            velocity = {}
            for param_name in self.parameter_names:
                position[param_name] = self.sample_from_space(param_name)
                velocity[param_name] = random.uniform(-1, 1)

            # Create a new Particle instance
            particle = Particle(position, velocity)
            self.particles.append(particle)

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
        elif param_type == 'payout':
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

    async def evaluate_fitness(self, particle):
        try:
            decoded_particle = self.enforce_constraints(particle)
            sim_result = await self.simulator.run(self.initial_balance, self.game_results, decoded_particle)
            fitness = sim_result[0].get_metric()
            print(f"Particle: {decoded_particle}, Fitness: {fitness}")
        except Exception as e:
            print(f"Error evaluating fitness for particle {particle}: {e}")
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
        elif param_type == 'payout':
            return max(min(value, param_range[1]), param_range[0])
        elif param_type == 'checkbox':
            return bool(round(value))
        elif param_type == 'radio':
            return param_range[0]  # Always return the first option for radio
        else:
            raise ValueError(f"Unknown parameter type: {param_type}")

    def enforce_constraints(self, particle):
        return {param: self.enforce_constraint(param, value) for param, value in particle.items()}

    async def update_particles(self):
        for particle in self.particles:
            # Calculate the inertia component
            inertia = {key: self.w * particle.velocity[key] for key in particle.position.keys()}

            # Calculate the cognitive component
            cognitive = {key: self.c1 * random.random() * (particle.pbest_position[key] - particle.position[key])
                for key in particle.position.keys()}

            # Calculate the social component
            social = {key: self.c2 * random.random() * (self.gbest_position[key] - particle.position[key])
                for key in particle.position.keys()}

            # Update the velocity of the particle
            for key in particle.velocity.keys():
                particle.velocity[key] = inertia[key] + cognitive[key] + social[key]

            # Update the position of the particle and enforce constraints
            for key in particle.position.keys():
                particle.position[key] += particle.velocity[key]
                particle.position[key] = self.enforce_constraint(key, particle.position[key])

            # Evaluate the fitness of the particle
            fitness = await self.evaluate_fitness(particle.position)
            print(f"Particle has a fitness of {fitness}")  # Debugging log

            # Update personal and global bests
            if fitness < particle.pbest_value:
                particle.pbest_position = particle.position.copy()
                particle.pbest_value = fitness

            if fitness < self.gbest_value:
                self.gbest_position = particle.position.copy()
                self.gbest_value = fitness

        logging.info(f"Current best fitness: {self.gbest_value}")

    async def optimize(self):
        for iter_num in range(self.current_iteration, self.max_iter):
            self.current_iteration = iter_num
            logging.info(f"Iteration {iter_num + 1}")
            await self.update_particles()
            self.save_optimization_state()

        self.save_final_result()
        logging.info(f"Optimization complete. Best position: {self.gbest_position}, Best value: {self.gbest_value}")
        return {'best_parameters': self.gbest_position, 'best_metric': self.gbest_value}

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
            "gbest_position": self.gbest_position,
            "status": "completed",
            "current_iteration": self.current_iteration
        }
        self.storage.update_optimization(self.optimization_id, final_state)
