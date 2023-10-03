import numpy as np
import logging
import asyncio
import random
import math
import traceback
from simulator import Simulator
from script import Script
from copy import deepcopy
from typing import List, Tuple, Dict
from operator import itemgetter

logging.basicConfig(level=logging.INFO)

class Optimizer:
    def __init__(self, script: Script, initial_balance: int, game_results, parameter_names: List[str], space):
        self.script = script
        self.initial_balance = initial_balance
        self.game_results = game_results
        self.parameter_names = parameter_names
        self.space = space
        self.population_size = 20
        self.max_generations = 100
        self.crossover_rate = 0.8
        self.mutation_rate = 0.2
        self.best_individual = None

    def sample_from_space(self, param_name, param_type, param_values):
        if param_type == 'continuous':
            return random.uniform(param_values[0], param_values[1])
        elif param_type == 'integer':
            return random.randint(param_values[0], param_values[1])
        elif param_type == 'categorical':
            return random.choice(param_values)
        else:
            raise ValueError(f"Unknown parameter type {param_type}")

    def initialize_population(self):
        population = []
        for _ in range(self.population_size):
            individual = {
                param_name: self.sample_from_space(
                    param_name, param_type, param_values
                )
                for param_name, param_values, param_type in self.space
            }
            population.append(individual)
        return population

    async def evaluate_fitness(self, individual):
        self.script.set_params(**individual)
        simulator = Simulator(self.script)
        try:
            results = await simulator.run(self.initial_balance, self.game_results)
            if results["results"] is None:
                raise ValueError("Simulation produced invalid results.")
            fitness_value = results["results"].get_metric()
        except Exception as e:
            logging.warning(f"Failed to evaluate individual {individual} due to exception: {e}. Assigning worst fitness.")
            traceback.print_exc()
            fitness_value = float('inf')
        
        return (individual, fitness_value)
    
    async def evaluate_population(self, population):
        tasks = [self.evaluate_fitness(individual) for individual in population]
        return await asyncio.gather(*tasks)
    
    def select_individuals(self, evaluated_population: List[Tuple[Dict, float]]) -> List[Dict]:
        sorted_population = sorted(evaluated_population, key=itemgetter(1), reverse=True)
        selected_individuals = sorted_population[:self.population_size // 2]
        return [individual for individual, _ in selected_individuals]

    def crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        crossover_point = len(self.parameter_names) // 2
        child = deepcopy(parent1)
        child.update({param: parent2[param] for param in self.parameter_names[crossover_point:]})
        return child

    def mutate(self, individual: Dict) -> Dict:
        mutation_param = np.random.choice(self.parameter_names)
        param_index = [i for i, (name, _, _) in enumerate(self.space) if name == mutation_param][0]
        individual[mutation_param] = self.sample_from_space(mutation_param, self.space[param_index][2], self.space[param_index][1])
        return individual

    def generate_new_population(self, selected_individuals: List[Dict]) -> List[Dict]:
        new_population = deepcopy(selected_individuals)
        while len(new_population) < self.population_size:
            if np.random.rand() < self.crossover_rate:
                parent1, parent2 = np.random.choice(selected_individuals, 2, replace=False)
                child = self.crossover(parent1, parent2)
                new_population.append(child)
            else:
                individual = np.random.choice(selected_individuals)
                mutated_individual = self.mutate(individual)
                new_population.append(mutated_individual)
        return new_population

    async def run_optimization(self) -> Dict:
        population = self.initialize_population()
        for generation in range(self.max_generations):
            evaluated_population = await self.evaluate_population(population)
            if not self.best_individual or max(evaluated_population, key=itemgetter(1))[1] > self.best_individual[1]:
                self.best_individual = max(evaluated_population, key=itemgetter(1))
            logging.info(f"Generation {generation}, Best Evaluation Metric: {self.best_individual[1]}")
            selected_individuals = self.select_individuals(evaluated_population)
            population = self.generate_new_population(selected_individuals)
        logging.info(f"Optimization complete. Best Parameters: {self.best_individual[0]}, Best Metric: {self.best_individual[1]}")
        return {"best_parameters": self.best_individual[0], "best_metric": self.best_individual[1]}
