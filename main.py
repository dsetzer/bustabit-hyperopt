import argparse
from itertools import product
import numpy as np
from prettytable import PrettyTable
from script import Script
from simulator import Simulator

def select_parameters(config_dict):
    parameters = []
    print("Select parameters to optimize:")

    # Create a table to display available parameters
    available_params_table = PrettyTable()
    available_params_table.field_names = ["#", "Parameter"]
    for idx, key in enumerate(config_dict.keys()):
        available_params_table.add_row([idx + 1, key])
    print(available_params_table)

    # Function to print selected parameters in a table
    def print_selected_parameters():
        selected_params_table = PrettyTable()
        selected_params_table.field_names = ["Parameter", "Min", "Max", "Step"]
        for param in parameters:
            selected_params_table.add_row([param[0], param[1], param[2], param[3]])
        print("\nSelected Parameters:")
        print(selected_params_table)

    while True:
        choice = input("Select a parameter by number (or 'done' to finish): ")
        if choice.lower() == 'done':
            break
        try:
            # Handle selection using table index
            selected_key = list(config_dict.keys())[int(choice) - 1]
            selected_type = config_dict[selected_key]['type']
            if selected_type == 'multiplier':
                min_value = float(input(f"Enter min value for {selected_key}: "))
                if min_value < 1.01 or min_value > 1e6:
                    print("Invalid min value. Please try again.")
                    continue
                max_value = float(input(f"Enter max value for {selected_key}: "))
                if max_value < 1.01 or max_value > 1e6:
                    print("Invalid max value. Please try again.")
                    continue
                step_value = float(input(f"Enter step value for {selected_key}: "))
            elif selected_type == 'balance':
                min_value = float(input(f"Enter min value for {selected_key}: "))
                if min_value < 100:
                    print("Invalid min value. Please try again.")
                    continue
                max_value = float(input(f"Enter max value for {selected_key}: "))
                if max_value < 100:
                    print("Invalid max value. Please try again.")
                    continue
                step_value = float(input(f"Enter step value for {selected_key}: "))
                if step_value < 100:
                    print("Invalid step value. Please try again.")
                    continue
            elif selected_type == 'number':
                min_value = float(input(f"Enter min value for {selected_key}: "))
                max_value = float(input(f"Enter max value for {selected_key}: "))
                step_value = float(input(f"Enter step value for {selected_key}: "))
            elif selected_type == 'checkbox':
                min_value = 0
                max_value = 1
                step_value = 1
            else:
                print("Invalid type. Please try again.")
                continue
            parameters.append((selected_key, min_value, max_value, step_value))
            print_selected_parameters()
        except (ValueError, IndexError):
            print("Invalid choice. Please try again.")
    return parameters

def generate_parameter_combinations(parameters):
    keys = [param[0] for param in parameters]
    value_ranges = [list(np.arange(param[1], param[2] + param[3], param[3])) for param in parameters]
    combinations = [dict(zip(keys, values)) for values in product(*value_ranges)]
    return combinations

def print_parameter_combinations(combinations):
    print("\nGenerated Parameter Combinations:")
    for idx, combination in enumerate(combinations, 1):
        print(f"{idx}. {combination}")

def objective(params):
    global parameter_names, script_obj, initial_balance, game_hash, num_games

    # Set the parameters in the script object
    param_dict = {key: value for key, value in zip(parameter_names, params)}
    script_obj.set_params(**param_dict)
    
    # Create and run the simulator
    simulator = Simulator(script_obj, initial_balance, game_hash, num_games)
    simulator.run(print_statistics=True)
    
    # Get the metric to optimize
    metric = simulator.get_metric()
    logger.info(f"Metric: {metric}")
    # Since we're using gp_minimize, we want to minimize the metric.
    # If you want to maximize the metric, return -metric
    return metric

def main():
    global parameter_names, script_obj, initial_balance, game_hash, num_games

    parser = argparse.ArgumentParser(description='Optimize parameters in a JS script.')
    parser.add_argument('--script', help='Path to the JavaScript file.')
    parser.add_argument('--params', help='Parameters to optimize in key:min,max,step format.')
    parser.add_argument('--hash', default='random_hash', help='Game hash to use for the simulation. Defaults to a random hash.')
    parser.add_argument('--games', type=int, default=1000, help='Number of games to simulate. Defaults to 1000.')
    parser.add_argument('--balance', type=float, default=10000, help='Initial balance in bits. Defaults to 10000.')

    args = parser.parse_args()

    game_hash = args.hash
    num_games = args.games
    initial_balance = args.balance

    if args.script and args.params:
        # Non-Interactive Mode
        script_obj = Script(args.script)
        params_list = args.params.split()
        parameters = [(param.split(':')[0], *map(float, param.split(':')[1].split(','))) for param in params_list]
    else:
        # Interactive Mode
        js_file_path = input("Enter the path to the JavaScript file: ")
        script_obj = Script(js_file_path)
        parameters = select_parameters(script_obj.config_dict)

        # Ask for additional parameters
        game_hash = None
        while True:
            game_hash = input("Enter the game hash (or press enter to use a random hash): ")
            if not game_hash:
                # Generate a random hash if the input is empty
                game_hash = hashlib.sha256(os.urandom(16)).hexdigest()
                print(f"Using random hash: {game_hash}")
                break
            elif len(game_hash) % 2 == 0:
                try:
                    bytes.fromhex(game_hash)
                    break
                except ValueError:
                    print("Invalid hexadecimal string. Please try again.")
            else:
                print("Hexadecimal string should have an even number of characters. Please try again.")
        num_games = int(input("Enter the number of games to simulate (or press enter to use 1000): ") or 1000)
        initial_balance = float(input("Enter the initial balance in bits (or press enter to use 10000): ") or 10000)

    print("Parameters:")
    for param in parameters:
        print(param)

    # List of parameter names
    parameter_names = [param[0] for param in parameters]

    # Bounds for the parameters
    bounds = [(param[1], param[2]) for param in parameters]

    # Initial values for the parameters
    x0 = [param[1] for param in parameters]

    # # Run the optimization
    # res = gp_minimize(objective, bounds, x0=x0)

    # logging.info("Optimization complete!")
    # logging.info(f"Optimal parameters: {res.x}")
    # logging.info(f"Optimal metric: {res.fun}")
    
    # Run the simulation
    simulator = Simulator(script_obj, initial_balance, game_hash, num_games)
    simulator.run(print_statistics=True)

if __name__ == "__main__":
    main()