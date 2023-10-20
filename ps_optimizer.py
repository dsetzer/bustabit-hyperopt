import numpy as np
from simulator import Simulator
from math import exp, log
import random

def decode_value(encoded_value, param_details):
    param_type = param_details.get('type')
    param_range = param_details.get('range')
    
    if param_type == 'continuous':
        return param_range[0] + (param_range[1] - param_range[0]) * (encoded_value / 100.0)
    
    if param_type == 'integer':
        return int(param_range[0] + round((param_range[1] - param_range[0]) * (encoded_value / 100.0)))
    
    if param_type == 'categorical':
        index = int(round((len(param_range) - 1) * (encoded_value / 100.0)))
        return param_range[index]
    
    if param_type == 'payout':
        return round(param_range[0] + (param_range[1] - param_range[0]) * (encoded_value / 100.0), 2)
    
    if param_type == 'checkbox':
        return bool(round(encoded_value / 100.0))

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

        self.simulator = Simulator(self.script_obj)
        
        self.initialize_particles()
        
        self.gbest_value = float('inf')
        self.gbest_position = {key: self.sample_from_space(key) for key in self.parameter_names}

    def sample_from_space(self, param_name):
        param_details = self.space.get(param_name, {})
        param_type = param_details.get('type')
        param_range = param_details.get('range')

        if param_type == 'continuous':
            return np.random.uniform(param_range[0], param_range[1])
        elif param_type == 'integer':
            return np.random.randint(param_range[0], param_range[1] + 1)
        elif param_type == 'categorical':
            return np.random.choice(param_range)
        elif param_type == 'payout':
            u = np.random.random()
            min_val, max_val = param_range
            normalization = 0.99 * log(max_val) - 0.99 * log(min_val)
            return exp(u * normalization + 0.99 * log(min_val))

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
        decoded_particle = {k: decode_value(v, self.space[k]) for k, v in particle.items()}
        sim_result = await self.simulator.run(self.initial_balance, self.game_results, decoded_particle)
        fitness = sim_result[0].get_metric()
        print(f"Particle: {decoded_particle}, Fitness: {fitness}")
        return fitness

    def enforce_constraints(self, particle):
        for param, value in particle.items():
            param_details = self.space.get(param, {})
            param_type = param_details.get('type')
            
            if param_type == 'number':
                value = max(min(value, param_details.get('range')[1]), param_details.get('range')[0])
                particle[param] = round(value)
                
            elif param_type == 'payout':
                value = max(min(value, param_details.get('range')[1]), param_details.get('range')[0])
                particle[param] = round(value, 2)  # Assuming 2 decimal places are needed
                
            elif param_type == 'balance':
                value = max(min(value, param_details.get('range')[1]), param_details.get('range')[0])
                particle[param] = round(value / 100) * 100  # Must be divisible by 100
                
            elif param_type == 'checkbox':
                particle[param] = bool(value)
                
            elif param_type == 'radio':
                value = max(min(value, param_details.get('range')[1]), param_details.get('range')[0])
                particle[param] = round(value)
        
        return particle

    async def update_particles(self):
        for i in range(self.num_particles):
            # Update velocity
            inertia = {key: self.w * self.velocities[i][key] for key in self.particles[i].keys()}
            cognitive = {key: self.c1 * random.random() * (self.pbest_position[i][key] - self.particles[i][key]) for key in self.particles[i].keys()}
            if self.gbest_position is not None:
                social = {key: self.c2 * random.random() * (self.gbest_position[key] - self.particles[i][key]) for key in self.particles[i].keys()}
            else:
                social = {key: 0 for key in self.particles[i].keys()}
            self.velocities[i] = {key: inertia[key] + cognitive[key] + social[key] for key in self.particles[i].keys()}

            # Update position and enforce constraints
            for key in self.particles[i].keys():
                self.particles[i][key] += self.velocities[i][key]
                self.particles[i] = self.enforce_constraints(self.particles[i])

            # Evaluate fitness
            fitness = await self.evaluate_fitness(self.particles[i])

            # Update personal and global bests
            if fitness < self.pbest_value[i]:
                self.pbest_position[i] = self.particles[i].copy()
                self.pbest_value[i] = fitness

            if self.gbest_position is None or fitness < self.gbest_value:
                self.gbest_position = self.particles[i].copy()
                self.gbest_value = fitness
                
    async def optimize(self):
        for iter_num in range(self.max_iter):
            print(f"Iteration {iter_num + 1}")
            await self.update_particles()
        
        print(f"Optimization complete. Best position: {self.gbest_position}, Best value: {self.gbest_value}")
        return self.gbest_position, self.gbest_value
