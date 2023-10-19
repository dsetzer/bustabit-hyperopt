import heapq
import numpy as np
import asyncio
from math import exp, log
from simulator import Simulator
from prettytable import PrettyTable
import logging
from memory_profiler import profile


class Optimizer:
    def __init__(self, script_obj, initial_balance, game_results, parameter_names, space):
        self.script_obj = script_obj
        self.initial_balance = initial_balance
        self.game_results = game_results
        self.parameter_names = parameter_names
        self.space = space
        self.evaluated_params = {}  
        
        self.population_size = 10  # Increased for more diversity
        self.num_generations = 30  # Increased to allow more refinement over time
        self.elite_size = 5  # Increased to retain more top performers
        self.tournament_size = 5  # Kept the same, adjust based on performance
        self.max_mutation_rate = 0.9  # Decreased to preserve good solutions
        self.min_mutation_rate = 0.1  # Set a floor to maintain some level of diversity
        self.max_crossover_rate = 0.9  # Kept the same to encourage recombination
        self.min_crossover_rate = 0.1  # Increased floor to ensure enough recombination
        
        self.simulator = Simulator(self.script_obj)  


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

    def initialize_population(self):
        population = np.array([
            {param: self.sample_from_space(param) for param in self.parameter_names}
            for _ in range(self.population_size)
        ])
        return population

    def select_parents_tournament(self, population, fitness):
        selected_parents = []
        for _ in range(len(population) - self.elite_size):
            tournament_individuals = np.random.choice(
                np.arange(len(population)),
                size=self.tournament_size,
                replace=False
            )
            tournament_fitness = fitness[tournament_individuals]
            tournament_winner = population[tournament_individuals[np.argmin(tournament_fitness)]]
            selected_parents.append(tournament_winner)
        return selected_parents

    def crossover(self, parent1, parent2, crossover_rate):
        if np.random.random() >= crossover_rate:
            return parent1, parent2
        
        crossover_point = np.random.randint(1, len(self.parameter_names))
        child1 = {param: parent1[param] if idx < crossover_point else parent2[param] for idx, param in enumerate(self.parameter_names)}
        child2 = {param: parent2[param] if idx < crossover_point else parent1[param] for idx, param in enumerate(self.parameter_names)}
        
        return child1, child2

    def mutate(self, individual, mutation_rate):
        mutated_individual = individual.copy()
        for param in self.parameter_names:
            if np.random.random() < mutation_rate:
                mutated_individual[param] = self.sample_from_space(param)
        return mutated_individual

    def round_parameters(self, individual):
        """Round the real and payout parameters to three decimal places."""
        for param, details in self.space.items():
            if details['type'] in ['continuous', 'payout']:
                individual[param] = round(individual[param], 2)
        return individual

    async def evaluate_population(self, population):
        tasks = []
        fitness = np.zeros(len(population))

        for i, individual in enumerate(population):
            individual = self.round_parameters(individual)
            params_tuple = tuple(individual.items())

            if params_tuple in self.evaluated_params:
                fitness[i] = -self.evaluated_params[params_tuple]  # Negating the fitness value
                logging.debug(f"Individual {i} already evaluated. Fitness: {fitness[i]}")
            else:
                tasks.append((i, self.simulator.run(self.initial_balance, self.game_results, individual)))
                logging.debug(f"Individual {i} not evaluated. Adding to tasks.")

        results = await asyncio.gather(*(task for _, task in tasks), return_exceptions=True)

        for (i, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logging.error(f"Error evaluating individual {i}: {result}")
                fitness[i] = float('inf')  # Setting the fitness to infinity
            else:
                fit = result['results'].get_metric()
                fitness[i] = -fit  # Negating the fitness value
                self.evaluated_params[tuple(population[i].items())] = fit

        return fitness
    async def run_optimization(self):
        population = self.initialize_population()
        results_dict = {}   
        top_5_results = []  
        unique_individuals = set()  # To store unique individuals
        
        for generation in range(self.num_generations):
            mutation_rate = self.max_mutation_rate - (generation / self.num_generations) * (self.max_mutation_rate - self.min_mutation_rate)
            crossover_rate = self.min_crossover_rate + (generation / self.num_generations) * (self.max_crossover_rate - self.min_crossover_rate)

            fitness = await self.evaluate_population(population)

            # Debugging to ensure that the best fitness is improving over generations
            logging.debug(f"Generation {generation}: Best Fitness: {-min(fitness)}")

            # Update top 5 results
            for individual, fit in zip(population, fitness):
                if fit != float('inf'):  # Check if the fitness is not infinity
                    individual_tuple = tuple(individual.items())
                    
                    if individual_tuple not in unique_individuals:
                        unique_individuals.add(individual_tuple)

                        if len(top_5_results) < 5:
                            heapq.heappush(top_5_results, (fit, individual))  # Storing the fitness value
                        elif fit < top_5_results[0][0]:  # Getting the actual fitness value
                            heapq.heappushpop(top_5_results, (fit, individual))

                        # Store the individual's parameters in the dictionary using fitness as the key
                        results_dict[fit] = individual

            # Elite selection
            elite_indices = np.argsort(fitness)[:self.elite_size]  # Sorting in ascending order
            elite_individuals = population[elite_indices]

            # Tournament selection for parents
            parents = self.select_parents_tournament(population, fitness)

            # Crossover and mutation to produce children
            children = []
            while len(children) < len(population) - self.elite_size:
                parent1 = np.random.choice(parents)
                parent2 = np.random.choice(parents)
                child1, child2 = self.crossover(parent1, parent2, crossover_rate)
                child1 = self.mutate(child1, mutation_rate)
                child2 = self.mutate(child2, mutation_rate)
                children.extend((child1, child2))

            # Next generation becomes the elite and children
            population = np.concatenate((elite_individuals, children[:len(population) - self.elite_size]), axis=0)

        # Final evaluation to update the fitness values
        fitness = await self.evaluate_population(population)
        best_individual_index = np.argmin(fitness)  # Getting the index of the individual with the lowest fitness value
        best_individual = population[best_individual_index]

        # Sort the top 5 results in ascending order
        top_5_results = sorted(top_5_results, key=lambda x: x[0])
        top_5_parameters = [(rank, {'parameters': individual, 'metric': -fit}) for rank, (fit, individual) in enumerate(top_5_results)]

        return {
            "best_parameters": {param: best_individual[param] for param in self.parameter_names},
            "best_metric": -fitness[best_individual_index],  # Negating the fitness value
            "top_5_results": top_5_parameters
        }