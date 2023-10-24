import numpy as np
from simulator import Simulator
from math import exp, log
import random
import logging

class PSOptimizer:
    def __init__(self, script_obj, initial_balance, game_results, parameter_names, space):
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
        
        self.initialize_particles()
        
        self.gbest_value = float('inf')
        self.gbest_position = {key: 0.0 for key in self.particles[0].keys()}

    def sample_from_space(self, param_name):
        param_details = self.space.get(param_name, {})
        param_type = param_details.get('type')
        param_range = param_details.get('range')

        if param_type == 'balance':
            return round(random.uniform(param_range[0], param_range[1]) / 100) * 100
        elif param_type == 'number':
            # check if it's an integer or float
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
            return param_range[0]

    def initialize_particles(self):
        self.particles = []
        self.velocities = []
        self.pbest_position = []
        self.pbest_value = []
        
        for _ in range(self.num_particles):
            # Initialize particle with encoded values
            particle = {}
            for param_name in self.parameter_names:
                encoded_value = random.uniform(0, 100)
                particle[param_name] = encoded_value
            self.particles.append(particle)
            
            # Initialize velocity
            velocity = {}
            for key in particle.keys():
                velocity[key] = random.uniform(-1, 1)
            self.velocities.append(velocity)

            # Initialize personal best
            self.pbest_position.append(particle.copy())
            self.pbest_value.append(float('inf'))

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

    def enforce_constraints(self, particle):
        for param, value in particle.items():
            param_details = self.space.get(param, {})
            param_type = param_details.get('type')
            param_range = param_details.get('range')
            
            if param_type == 'number':
                value = max(min(value, param_range[1]), param_range[0])
                if param_details.get('is_integer'):
                    value = round(value)
                particle[param] = value
                
            elif param_type == 'payout':
                value = max(min(value, param_range[1]), param_range[0])
                particle[param] = round(value, 2)  # Assuming 2 decimal places are needed
                
            elif param_type == 'balance':
                value = max(min(value, param_range[1]), param_range[0])
                value = max(0, round(value / 100) * 100)  # Must be non-negative and divisible by 100
                particle[param] = value
                
            elif param_type == 'checkbox':
                particle[param] = bool(round(value / 100.0))
                
            elif param_type == 'radio':
                particle[param] = param_range[0]

        return particle

    async def update_particles(self):
        for i in range(self.num_particles):
            # Calculate the inertia component for each particle
            inertia = {key: self.w * self.velocities[i][key] for key in self.particles[i].keys()}

            # Calculate the cognitive component safely by checking for None values
            cognitive = {}
            for key in self.particles[i].keys():
                pbest_value = self.pbest_position[i].get(key)
                particle_value = self.particles[i].get(key)

                if pbest_value is None or particle_value is None:
                    print(f"Warning: Encountered None value for key '{key}' in particle {i}. Skipping this key.")
                    continue
                    
                cognitive[key] = self.c1 * random.random() * (pbest_value - particle_value)

            # Calculate the social component for each particle
            social = {key: self.c2 * random.random() * (self.gbest_position[key] - self.particles[i][key]) for key in self.particles[i].keys()}

            # Update the velocity of each particle
            self.velocities[i] = {key: inertia[key] + cognitive.get(key, 0) + social[key] for key in self.particles[i].keys()}

            # Update the position of each particle and enforce constraints
            for key, value in self.particles[i].items():
                self.particles[i][key] += self.velocities[i][key]

                if self.space[key]['type'] == 'checkbox':
                    self.particles[i][key] = self.particles[i][key] >= 0
                elif self.space[key]['type'] in ['balance', 'multiplier']:
                    self.particles[i][key] = abs(self.particles[i][key])

            # Evaluate the fitness of each particle
            fitness = await self.evaluate_fitness(self.particles[i])
            print(f"Particle {i} has a fitness of {fitness}")  # Debugging log

            # Update personal and global bests
            if fitness < self.pbest_value[i]:
                self.pbest_position[i] = self.particles[i].copy()
                self.pbest_value[i] = fitness

            if fitness < self.gbest_value:
                self.gbest_position = self.particles[i].copy()
                self.gbest_value = fitness

        logging.info(f"Current best fitness: {self.gbest_value}")

    async def optimize(self):
        for iter_num in range(self.max_iter):
            logging.info(f"Iteration {iter_num + 1}")
            await self.update_particles()

        logging.info(f"Optimization complete. Best position: {self.gbest_position}, Best value: {self.gbest_value}")
        return {'best_parameters': self.gbest_position, 'best_metric': self.gbest_value, 'top_5_results': []}