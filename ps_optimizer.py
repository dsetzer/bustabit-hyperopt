import numpy as np
import asyncio
from simulator import Simulator
from math import exp, log

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
        
        self.pbest_position = np.copy(self.particles)
        self.pbest_value = np.full((self.num_particles,), float('inf'))
        self.gbest_value = float('inf')
        self.gbest_position = None

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
        self.particles = np.array([
            {param: self.sample_from_space(param) for param in self.parameter_names}
            for _ in range(self.num_particles)
        ])

    async def evaluate_fitness(self, particle):
        sim_result = await self.simulator.run(self.initial_balance, self.game_results, particle)
        fitness = sim_result[0].get_metric()
        print(f"Particle: {particle}, Fitness: {fitness}")
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
            # Evaluate the fitness of each particle
            fitness = await self.evaluate_fitness(self.particles[i])
            
            # Update the personal best for this particle
            if fitness < self.pbest_value[i]:
                self.pbest_value[i] = fitness
                self.pbest_position[i] = self.particles[i]
            
            # Update the global best
            if fitness < self.gbest_value:
                self.gbest_value = fitness
                self.gbest_position = self.particles[i]
            
            # Enforce the constraints for each particle
            self.particles[i] = self.enforce_constraints(self.particles[i])
                
    async def optimize(self):
        for iter_num in range(self.max_iter):
            print(f"Iteration {iter_num + 1}")
            await self.update_particles()

            # Update velocity and position
            for i in range(self.num_particles):
                new_velocity = (self.w * np.random.random()) + \
                               (self.c1 * np.random.random() * (np.array(list(self.pbest_position[i].values())) - np.array(list(self.particles[i].values())))) + \
                               (self.c2 * np.random.random() * (np.array(list(self.gbest_position.values())) - np.array(list(self.particles[i].values()))))
                
                self.particles[i] = {self.parameter_names[j]: new_velocity[j] for j in range(len(self.parameter_names))}
        print(f"Optimization complete. Best position: {self.gbest_position}, Best value: {self.gbest_value}")
        return self.gbest_position, self.gbest_value
