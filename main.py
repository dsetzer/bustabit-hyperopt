import argparse
import asyncio
import hashlib
import logging
import math
import os
import sys
import time
from functools import partial
from itertools import product

import numpy as np
from prettytable import PrettyTable
from skopt import gp_minimize
from skopt.space import Categorical, Integer, Real, Space
from skopt.utils import use_named_args
from skopt.callbacks import DeltaYStopper

from script import Script
from simulator import GameResults, Simulator

def get_default_range(param_type, default_value):
    if param_type == 'multiplier':
        return (1.01, 1e6), 'continuous'
    elif param_type == 'balance':
        return (100, 1000000), 'integer'
    elif param_type == 'number':
        if isinstance(default_value, int):
            return (math.floor(default_value * 0.5), math.ceil(default_value * 1.5)), 'integer'
        else:
            return (default_value * 0.5, default_value * 1.5), 'continuous'
    elif param_type == 'checkbox':
        return [True, False], 'categorical'
    elif param_type == 'radio' or param_type == 'combobox':
        return list(default_value.keys()), 'categorical'
    else:
        return None

def select_parameters(config_dict):
    parameters = []
    print("Select parameters to optimize:")

    # Create a table to display available parameters
    available_params_table = PrettyTable()
    available_params_table.field_names = ["#", "Parameter", "Input Type", "Default Value"]
    for idx, key in enumerate(config_dict.keys()):
        available_params_table.add_row([idx + 1, key, config_dict[key]['type'], config_dict[key]['value']])
    print(available_params_table)

    # Function to print selected parameters in a table
    def print_selected_parameters():
        selected_params_table = PrettyTable()
        selected_params_table.field_names = ["Parameter", "Value Range", "Type"]
        for param in parameters:
            if param[2] == 'categorical':
                value_range = ', '.join(map(str, param[1]))
            else:
                value_range = f"{param[1][0]} to {param[1][1]}"
            selected_params_table.add_row([param[0], value_range, param[2]])

        print("\nSelected Parameters:")
        print(selected_params_table)

    while True:
        choice = input("Choose a parameter by its number, enter 'done' to complete the selection, or type 'auto' for automatic setup: ")
        if choice.lower() == 'auto':
            for idx, key in enumerate(config_dict.keys()):
                selected_type = config_dict[key]['type']
                param_range = get_default_range(selected_type, config_dict[key]['value'])  # Define this function to get the default range for each type
                parameters.append((key, param_range[0], param_range[1]))
            
            print_selected_parameters()
            return parameters
            
        elif choice.lower() == 'done':
            break
        try:
            # Handle selection using table index
            selected_key = list(config_dict.keys())[int(choice) - 1]
            selected_type = config_dict[selected_key]['type']
            
            # multiplier parameter
            if selected_type == 'multiplier':
                min_value = float(input(f"Enter min value for {selected_key}: "))
                if min_value < 1.01 or min_value > 1e6:
                    print("Invalid min value. Please try again.")
                    continue
                max_value = float(input(f"Enter max value for {selected_key}: "))
                if max_value < 1.01 or max_value > 1e6:
                    print("Invalid max value. Please try again.")
                    continue
                param_type = 'continuous'
                parameters.append((selected_key, (min_value, max_value), param_type))
                
            # balance parameter                
            elif selected_type == 'balance':
                min_value = int(float(input(f"Enter min value for {selected_key}: ")) * 100)
                if min_value < 100:
                    print("Invalid min value. Please try again.")
                    continue
                max_value = int(float(input(f"Enter max value for {selected_key}: ")) * 100)
                if max_value < 100:
                    print("Invalid max value. Please try again.")
                    continue
                param_type = 'integer'
                parameters.append((selected_key, (min_value, max_value), param_type))
            
            # number parameter
            elif selected_type == 'number':
                min_value = float(input(f"Enter min value for {selected_key}: "))
                max_value = float(input(f"Enter max value for {selected_key}: "))
                if min_value.is_integer() and max_value.is_integer():
                    response = input("Whole numbers only? (yes/no): ")
                    param_type = 'integer' if response.lower() == 'yes' else 'continuous'
                else:
                    param_type = 'continuous'
                parameters.append((selected_key, (min_value, max_value), param_type))
                    
            # checkbox parameter
            elif selected_type == 'checkbox':
                param_values = [True, False]
                param_type = 'categorical'
                parameters.append((selected_key, param_values, param_type))  
  
            # radio or combobox parameter
            elif selected_type == 'radio' or selected_type == 'combobox':
                # options are stored as an object in the form of `option1: { label: 'Option 1', type: 'noop', value: 1 }` within the `options` property of the config item
                options = config_dict[selected_key]['options']
                options_table = PrettyTable()
                options_table.field_names = ["#", "Option"]
                for idx, key in enumerate(options.keys()):
                    options_table.add_row([idx + 1, options[key]['label']])
                print(options_table)
                # allow the user to choose the options as a comma separated list of numbers (e.g. 1,2,3)
                option_choices = input("Select options by number (or 'all' to select all options): ")
                if option_choices.lower() == 'all':
                    param_values = list(options.keys())
                else:
                    param_values = [list(options.keys())[int(choice) - 1] for choice in option_choices.split(',')]
                param_type = 'categorical'
                parameters.append((selected_key, param_values, param_type))
            else:
                print("Invalid type. Please try again.")
                continue
            
            print_selected_parameters()
        except (ValueError, IndexError):
            print(f'Invalid choice. Please try again.')
    return parameters


def objective(params, param_names, script_obj: Script, initial_balance: int, game_results: GameResults):
    # Set the parameters in the script object
    param_dict = {key: value for key, value in zip(param_names, params)}
    script_obj.set_params(**param_dict)

    # Create and run the simulator
    simulator = Simulator(script_obj)
    loop = asyncio.get_event_loop()
    try:
        logging.info(f"Starting simulation with {initial_balance / 100} bits for {game_results.num_sets} sets of {game_results.num_games} games each.")
        result = loop.run_until_complete(simulator.run(initial_balance, game_results))
    except Exception as e:
        logging.error(f"Failed to run simulator: {e}")
        return 1e12  # Return a large value to indicate failure

    # Get the metric to optimize
    try:
        averaged_statistics = result["results"]
        metric = averaged_statistics.get_metric()
    except Exception as e:
        logging.error(f"Failed to get metric: {e}")
        return 1e12  # Return a large value to indicate failure

    logging.info(f"Params: {param_dict}, Metric: {metric}")

    # Since we're using gp_minimize, we want to minimize the metric.
    # If you want to maximize the metric, return -metric
    return metric


def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description='Optimize parameters in a JS script.')
    
    # Add arguments to the parser
    parser.add_argument('--script', help='Path to the JavaScript file.')
    parser.add_argument('--params', help='Parameters to optimize.')
    parser.add_argument('--games', type=int, default=1000, help='Number of games to simulate. Defaults to 1000.')
    parser.add_argument('--balance', type=float, default=10000, help='Initial balance in bits. Defaults to 10000 bits.')
    parser.add_argument('--required_median', type=float, default=2.00, help='Required median bust for simulations. Defaults to 2.00.')
    parser.add_argument('--num_sets', type=int, default=5, help='Number of sets for each simulation. Defaults to 5.')
    
    # Parse the arguments
    args = parser.parse_args()
    num_games = args.games
    initial_balance = int(args.balance * 100)  # convert to satoshis
    required_median = args.required_median
    num_sets = args.num_sets
    
    if args.script and args.params:
        # Non-Interactive Mode
        script_obj = Script(args.script)
        params_list = args.params.split(";")
        parameters = []
        for param in params_list:
            param_details = param.split(":")
            param_name = param_details[0]
            value_ranges = param_details[1].split(",")
            param_type = value_ranges[0]
            
            if param_type == "categorical":
                param_values = value_ranges[1:]
                parameters.append((param_name, param_values, param_type))
            else:
                min_value = float(value_ranges[1])
                max_value = float(value_ranges[2])
                parameters.append((param_name, (min_value, max_value), param_type))
    else:
        # Interactive Mode
        js_file_path = input("Enter the path to the JavaScript file: ")
        script_obj = Script(js_file_path)
        parameters = select_parameters(script_obj.config_dict)

        num_games = input("Enter the simulation size (number of games) [default: 1000]: ")
        num_games = int(num_games) if num_games else 1000

        initial_balance = input("Enter the initial balance in bits [default: 10000]: ")
        initial_balance = int(float(initial_balance) * 100) if initial_balance else 10000

        required_median = 1.98
        num_sets = 3
    
    # Create a GameResults object
    game_results = GameResults(required_median, num_sets, num_games)
    
    # List of parameter names
    parameter_names = [param[0] for param in parameters]

    # Initial values for the parameters
    x0 = [param[1][0] if param[2] != 'categorical' else param[1][0] for param in parameters]

    space = Space([Integer(param[1][0], param[1][1]) if param[2] == 'integer'
                   else Real(param[1][0], param[1][1]) if param[2] == 'continuous'
                   else Categorical(param[1]) for param in parameters])
    
    # Inform the user that the optimization is ready to start when they hit enter
    input("\nThe optimization is ready to start. Press enter to begin...")
    
    # Run the optimization
    np.int = np.int64  # to resolve any numpy int to python int mapping issues
    # Define early stopping callback
    delta_callback = DeltaYStopper(delta=1e-6, n_best=5)  # Stop if the best observed values are within 1e-6

    # Run the optimization with the callback
    res = gp_minimize(
        func=partial(objective, param_names=parameter_names, script_obj=script_obj, initial_balance=initial_balance, game_results=game_results),
        dimensions=space,
        n_calls=1000000000,  # Run for a long time
        n_initial_points=20,  # More initial points for better exploration
        acq_func='gp_hedge',  # Use hedged Gaussian Process
        x0=None, # [script_obj.config_dict.get(param[0], param[1][0]) for param in parameters],  # Use default values from script's config_dict
        y0=None,  # Use prior knowledge if available
        random_state=42,  # For reproducibility
        verbose=True,  # Good for debugging
        callback=[delta_callback],  # Added early stopping callback
        n_points=5000,  # Reduced for faster computation
        n_restarts_optimizer=10,  # More restarts for more robust optimization
        xi=0.02,  # Slightly more conservative exploration
        kappa=1.96,  # Not applicable since acq_func is 'EI'
        noise='gaussian',  # Assuming Gaussian noise
        n_jobs=-1  # Use all available cores
    )
    
    # Print command line to start the program in non-interactive mode
    params_cmd = " ".join([f"{param[0]}:{param[2]},{param[1][0]},{param[1][1]}" if param[2] != 'categorical' else f"{param[0]}:{param[2]},{''.join(param[1])}" for param in parameters])
    print(f"\nTo run the program in non-interactive mode, use the following command:")
    print(f"python optimizer.py --script {script_obj.js_file_path} --params \"{params_cmd}\" --games {num_games} --balance {initial_balance // 100} --required_median {required_median} --num_sets {num_sets}")

    # Log or print the optimization results
    logging.info("Optimization complete!")
    logging.info(f"Optimal parameters: {res.x}")
    logging.info(f"Optimal metric: {res.fun}")

    # Print the best parameters and their corresponding metric
    print(f"\nBest Parameters: {res.x}")
    print(f"Best Metric: {res.fun}")

    # Sort the history of evaluations to find the top 10 parameter sets
    sorted_indices = np.argsort(res.func_vals)
    top_10_indices = sorted_indices[:10]

    # Print the optimization history
    print("\nTop 10 Optimization Results:")
    for i, index in enumerate(top_10_indices):
        print(f"Rank {i+1}")
        print("  Parameters: ", res.x_iters[index])
        print("  Metric: ", res.func_vals[index])

if __name__ == "__main__":
    main()
