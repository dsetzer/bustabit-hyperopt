import argparse
import hashlib
import logging
import math
import numpy as np
import asyncio
from prettytable import PrettyTable
from script import Script
from simulator import GameResults
from storage import Storage
# from optimizer import Optimizer
from ps_optimizer import PSOptimizer as Optimizer
import gc
import tracemalloc

tracemalloc.start()
np.int = np.int64 # Fix for a bug in skopt

def get_default_range(param_type, default_value):
    if param_type == 'multiplier':
        return (1.01, 1e6), 'multiplier'
    elif param_type == 'balance':
        default_value = default_value / 100
        return (1, 10000), 'balance'
    elif param_type == 'number':
        if isinstance(default_value, int):
            return (math.floor(default_value * 0.5), math.ceil(default_value * 1.5)), 'number'
        else:
            return (default_value * 0.5, default_value * 1.5), 'number'
    elif param_type == 'checkbox':
        return [True, False], 'checkbox'
    elif param_type in ['radio', 'combobox']:
        return list(default_value.keys()), 'radio'
    else:
        return None

def select_parameters(config):
    parameters = []
    print("Select parameters to optimize:")
    available_params_table = PrettyTable()
    available_params_table.field_names = ["#", "Parameter", "Input Type", "Default Value"]
    for idx, key in enumerate(config.keys()):
        default_value = config[key]['value']
        if config[key]['type'] == 'balance':
            default_value = default_value / 100
        available_params_table.add_row([idx + 1, key, config[key]['type'], default_value])
    print(available_params_table)

    def print_selected_parameters():
        selected_params_table = PrettyTable()
        selected_params_table.field_names = ["Parameter", "Value Range", "Type"]
        for param in parameters:
            if param[2] == 'checkbox':
                value_range = ', '.join(map(str, param[1]))
            else:
                value_range = f"{param[1][0]} to {param[1][1]}"
            selected_params_table.add_row([param[0], value_range, param[2]])
        print("\\nSelected Parameters:")
        print(selected_params_table)

    while True:
        choice = input("Choose a parameter by its number, enter 'done' to complete the selection, or type 'auto' for automatic setup: ")
        if choice.lower() == 'auto':
            for idx, key in enumerate(config.keys()):
                selected_type = config[key]['type']
                param_range = get_default_range(selected_type, config[key]['value'])
                parameters.append((key, param_range[0], param_range[1]))
            print_selected_parameters()
            return parameters
        elif choice.lower() == 'done':
            break
        try:
            selected_key = list(config.keys())[int(choice) - 1]
            selected_type = config[selected_key]['type']
            if selected_type == 'multiplier':
                min_value = float(input(f"Enter min value for {selected_key}: "))
                if min_value < 1.01 or min_value > 1e6:
                    print("Invalid min value. Please try again.")
                    continue
                max_value = float(input(f"Enter max value for {selected_key}: "))
                if max_value < 1.01 or max_value > 1e6:
                    print("Invalid max value. Please try again.")
                    continue
                param_type = 'multiplier'
                parameters.append((selected_key, (min_value, max_value), param_type))
            elif selected_type == 'balance':
                min_value = int(float(input(f"Enter min value for {selected_key}: ")))
                if min_value < 1:
                    print("Invalid min value. Please try again.")
                    continue
                max_value = int(float(input(f"Enter max value for {selected_key}: ")))
                if max_value < 1:
                    print("Invalid max value. Please try again.")
                    continue
                param_type = 'balance'
                parameters.append((selected_key, (min_value, max_value), param_type))
            elif selected_type == 'number':
                min_value = float(input(f"Enter min value for {selected_key}: "))
                max_value = float(input(f"Enter max value for {selected_key}: "))
                if min_value.is_integer() and max_value.is_integer():
                    response = input("Whole numbers only? (yes/no): ")
                    param_type = 'number' if response.lower() == 'yes' else 'continuous'
                else:
                    param_type = 'number'
                parameters.append((selected_key, (min_value, max_value), param_type))
            elif selected_type == 'checkbox':
                param_values = [True, False]
                param_type = 'checkbox'
                parameters.append((selected_key, param_values, param_type))
            elif selected_type in ['radio', 'combobox']:
                options = config[selected_key]['options']
                options_table = PrettyTable()
                options_table.field_names = ["#", "Option"]
                for idx, key in enumerate(options.keys()):
                    options_table.add_row([idx + 1, options[key]['label']])
                print(options_table)
                option_choices = input("Select options by number (or 'all' to select all options): ")
                if option_choices.lower() == 'all':
                    param_values = list(options.keys())
                else:
                    param_values = [list(options.keys())[int(choice) - 1] for choice in option_choices.split(',')]
                param_type = 'radio'
                parameters.append((selected_key, param_values, param_type))
            else:
                print("Invalid type. Please try again.")
                continue
            print_selected_parameters()
        except (ValueError, IndexError):
            print('Invalid choice. Please try again.')
    return parameters
async def main():
    parser = argparse.ArgumentParser(description='Optimize parameters in a JS script.')
    parser.add_argument('--script', help='Path to the JavaScript file.')
    parser.add_argument('--params', help='Parameters to optimize.')
    parser.add_argument('--games', type=int, default=1000, help='Number of games to simulate. Defaults to 1000.')
    parser.add_argument('--balance', type=float, default=10000, help='Initial balance in bits. Defaults to 10000 bits.')
    args = parser.parse_args()
    num_games = args.games
    initial_balance = int(args.balance * 100)
    required_median = 1.98
    num_sets = 3

    storage = Storage('optimizations.db')

    if args.script and args.params:
        js_file_path = args.script
        script_obj = Script(js_file_path)
        num_games = args.games or 1000
        params_list = args.params.split(";")
        parameters = []
        for param in params_list:
            param_details = param.split(":")
            param_name = param_details[0]
            value_ranges = param_details[1].split(",")
            param_type = value_ranges[0]
            if param_type == "checkbox":
                param_values = [True if value == "True" else False for value in value_ranges[1:]]
                parameters.append((param_name, param_values, param_type))
            elif param_type == "radio":
                param_values = value_ranges[1:]
                parameters.append((param_name, param_values, param_type))
            else:
                min_value = float(value_ranges[1])
                max_value = float(value_ranges[2])
                parameters.append((param_name, (min_value, max_value), param_type))
    else:
        js_file_path = input("Enter the path to the JavaScript file: ")
        script_obj = Script(js_file_path)

        existing_scripts = storage.get_all_scripts()
        if existing_scripts:
            print("Existing scripts found:")
            for idx, script in enumerate(existing_scripts):
                print(f"{idx + 1}. ID: {script['id']}, Path: {script['path']}, Last Updated: {script['timestamp']}")

            choice = input("Enter the number of the script to reuse, or 'n' for a new script: ")
            if choice.lower() != 'n':
                script_id = existing_scripts[int(choice) - 1]['id']
                script_obj = storage.get_script_by_id(script_id)

        parameters = select_parameters(script_obj.config)

        num_games = input("Enter the simulation size (number of games) [default: 1000]: ")
        num_games = int(num_games) if num_games else 1000

        initial_balance = input("Enter the initial balance in bits [default: 10000]: ")
        initial_balance = int(float(initial_balance) * 100) if initial_balance else 1000000


    # Create the log file
    logging.basicConfig(filename=f"logs/{hashlib.md5(script_obj.js_file_path.encode()).hexdigest()}.log", level=logging.INFO)


    # Check if there's an existing optimization to resume
    existing_optimizations = storage.get_all_optimizations()
    if existing_optimizations:
        print("Existing optimizations found:")
        for idx, opt in enumerate(existing_optimizations):
            print(f"{idx + 1}. ID: {opt['id']}, Status: {opt['status']}, Last Updated: {opt['timestamp']}")

        choice = input("Enter the number of the optimization to resume, or 'n' for a new optimization: ")
        if choice.lower() != 'n':
            optimization_id = existing_optimizations[int(choice) - 1]['id']
            optimizer = Optimizer(script_obj, initial_balance, GameResults(required_median, num_sets, num_games), [param[0] for param in parameters], {param[0]: {'range': param[1], 'type': param[2]} for param in parameters}, optimization_id=optimization_id)
        else:
            # Generate the game result sets for the simulator
            game_results = GameResults(required_median, num_sets, num_games)

            # Build the parameter space for the optimizer
            parameter_names = [param[0] for param in parameters]
            space = {param[0]: {'range': param[1], 'type': param[2]} for param in parameters}
            # Create the optimizer and run the optimization
            optimizer = Optimizer(script_obj, initial_balance, GameResults(required_median, num_sets, num_games), [param[0] for param in parameters], {param[0]: {'range': param[1], 'type': param[2]} for param in parameters})
    else:
        # Generate the game result sets for the simulator
        game_results = GameResults(required_median, num_sets, num_games)

        # Build the parameter space for the optimizer
        parameter_names = [param[0] for param in parameters]
        space = {param[0]: {'range': param[1], 'type': param[2]} for param in parameters}
        optimizer = Optimizer(script_obj, initial_balance, GameResults(required_median, num_sets, num_games), [param[0] for param in parameters], {param[0]: {'range': param[1], 'type': param[2]} for param in parameters})

    # Start the optimization
    input("\nThe optimization is ready to start. Press enter to begin...")
    logging.info(f"Starting optimization with {initial_balance / 100} bits for {num_sets} sets of {num_games} games each.")
    optimization_results = await optimizer.optimize()

    # Save the final results
    optimizer.save_final_result()

    # Print cmd to run the program in non-interactive mode
    params_cmd = ";".join([f"{param[0]}:{param[2]},{param[1][0]},{param[1][1]}" if param[2] != 'checkbox' and param[2] != 'radio' else f"{param[0]}:{param[2]},{''.join(str(val) for val in param[1])}" for param in parameters])
    logging.info(f"\nTo run again in non-interactive mode, use the following command:")
    logging.info(f"python main.py --script {script_obj.js_file_path} --params \"{params_cmd}\" --games {num_games} --balance {initial_balance / 100}")

    # Logging the optimization results
    logging.info("\nOptimization complete!")
    logging.info(f"Best Parameters: {optimization_results['best_parameters']}")
    logging.info(f"Best Metric: {optimization_results['best_metric']}")
    logging.info("\nTop 5 Optimization Results:")
    for rank, result in optimization_results['top_5_results']:
        logging.info(f"Rank {rank + 1}")
        logging.info(f"  Parameters: {result['parameters']}")
        logging.info(f"  Metric: {result['metric']}")

    # Close the storage connection
    storage.close()

    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    print("\nn[ Top 10 ]")
    for stat in top_stats[:10]:
        print(stat)

    tracemalloc.stop()
if __name__ == "__main__":
    asyncio.run(main())
