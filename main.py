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

def main():
    parser = argparse.ArgumentParser(description='Optimize parameters in a JS script.')
    parser.add_argument('--script', help='Path to the JavaScript file.')
    parser.add_argument('--params', help='Parameters to optimize in key:min,max,step format.')

    args = parser.parse_args()

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

    print("Parameters:")
    for param in parameters:
        print(param)

    #combinations = generate_parameter_combinations(parameters)
    #print_parameter_combinations(combinations)

if __name__ == "__main__":
    main()
