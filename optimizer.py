import random
import asyncio
import numpy as np
from math import exp, log
from simulator import Simulator
from prettytable import PrettyTable
import logging

class Optimizer:
    def __init__(self, script_obj, initial_balance, game_results, parameter_names, space):
        self.script_obj = script_obj
        self.initial_balance = initial_balance
        self.game_results = game_results
        self.parameter_names = parameter_names
        self.space = space
        self.population_size = 20
        self.num_generations = 30
        self.elite_size = 4
        self.tournament_size = 5
        self.mutation_rate = 0.2
        self.simulator = Simulator(self.script_obj)  # Initialize the Simulator object here

    def sample_from_space(self, param_name):
        param_details = self.space.get(param_name, {})
        param_type = param_details.get('type')
        param_range = param_details.get('range')

        if param_type == 'continuous':
            return random.uniform(param_range[0], param_range[1])
        elif param_type == 'integer':
            return random.randint(param_range[0], param_range[1])
        elif param_type == 'categorical':
            return random.choice(param_range)
        elif param_type == 'payout':
            u = random.random()
            min_val, max_val = param_range
            normalization = 0.99 * log(max_val) - 0.99 * log(min_val)
            return exp(u * normalization + 0.99 * log(min_val))

    def initialize_population(self):
        population = []
        for _ in range(self.population_size):
            individual = {param: self.sample_from_space(param) for param in self.parameter_names}
            population.append(individual)
        return population

    def select_parents_tournament(self, population, fitness):
        selected_parents = []
        for _ in range(len(population) - self.elite_size):
            tournament_individuals = random.sample(list(zip(population, fitness)), self.tournament_size)
            tournament_winner = max(tournament_individuals, key=lambda x: x[1])[0]
            selected_parents.append(tournament_winner)
        return selected_parents

    def crossover(self, parent1, parent2):
        crossover_point = random.randint(1, len(self.parameter_names) - 1)
        child1 = {}
        child2 = {}
        for idx, param in enumerate(self.parameter_names):
            if idx < crossover_point:
                child1[param] = parent1[param]
                child2[param] = parent2[param]
            else:
                child1[param] = parent2[param]
                child2[param] = parent1[param]
        return child1, child2

    def mutate(self, individual):
        for param in self.parameter_names:
            if random.random() < self.mutation_rate:
                individual[param] = self.sample_from_space(param)
        return individual

    async def evaluate_population(self, population):
        tasks = [
            self.simulator.run(self.initial_balance, self.game_results, individual)
            for individual in population
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        fitness = []
        for result in results:
            if isinstance(result, Exception):
                logging.warning(f"Exception caught during simulation: {result}")
                fitness.append(float('-inf'))  # Append a low fitness score for failed simulations
            else:
                fitness.append(result['results'].get_metric())
        return fitness

    async def run_optimization(self):
        population = self.initialize_population()
        top_10_results = []

        for _ in range(self.num_generations):
            fitness = await self.evaluate_population(population)
            combined = list(zip(population, fitness))

            # Update top 10 results
            top_10_results.extend(combined)
            top_10_results = sorted(top_10_results, key=lambda x: x[1], reverse=True)[:10]

            # Elite selection
            elite_individuals = sorted(combined, key=lambda x: x[1], reverse=True)[:self.elite_size]
            elite_individuals = [individual for individual, _ in elite_individuals]

            # Tournament selection for parents
            parents = self.select_parents_tournament(population, fitness)

            # Crossover and mutation to produce children
            children = []
            while len(children) < len(population) - self.elite_size:
                parent1 = random.choice(parents)
                parent2 = random.choice(parents)
                child1, child2 = self.crossover(parent1, parent2)
                child1 = self.mutate(child1)
                child2 = self.mutate(child2)
                children.extend((child1, child2))

            # Next generation becomes the elite and children
            population = elite_individuals + children[:len(population) - self.elite_size]

        # Final evaluation to update the fitness values
        fitness = await self.evaluate_population(population)
        best_individual = max(list(zip(population, fitness)), key=lambda x: x[1])

        return {
            "best_parameters": best_individual[0],
            "best_metric": best_individual[1],
            "top_10_results": [{"rank": i + 1, "parameters": res[0], "metric": res[1]} for i, res in enumerate(top_10_results)]
        }

