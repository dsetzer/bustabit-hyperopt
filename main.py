
import argparse
from itertools import product
import numpy as np
from STPyV8 import JSContext, JSObject

def read_js_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        js_code = file.read()
    return js_code

def js_object_to_python(js_obj):
    python_dict = {}
    for key in js_obj.keys():
        value = js_obj[key]
        if isinstance(value, JSObject):
            python_dict[key] = js_object_to_python(value)
        else:
            python_dict[key] = value
    return python_dict

def extract_config_object(js_code):
    start_index = js_code.find('var config = {')
    if start_index == -1:
        raise FileNotFoundError("Config object not found")

    end_index = start_index
    brace_count = 0
    for i, char in enumerate(js_code[start_index:]):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                end_index = start_index + i
                break

    # Extract and evaluate only the config object definition
    config_code = js_code[start_index:end_index + 1]

    with JSContext() as ctxt:
        ctxt.eval(config_code)
        config_object = ctxt.eval("config")
        config_dict = js_object_to_python(config_object)

    return config_dict

def select_parameters(config_dict):
    parameters = []
    print("Select parameters to optimize:")
    for idx, key in enumerate(config_dict.keys()):
        print(f"{idx + 1}. {key}")

    while True:
        choice = input("Select a parameter by number (or 'done' to finish): ")
        if choice.lower() == 'done':
            break
        try:
            selected_key = list(config_dict.keys())[int(choice) - 1]
            min_value = float(input(f"Enter min value for {selected_key}: "))
            max_value = float(input(f"Enter max value for {selected_key}: "))
            step_value = float(input(f"Enter step value for {selected_key}: "))
            parameters.append((selected_key, min_value, max_value, step_value))
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
        # Split the params by space
        params_list = args.params.split()
        # Non-Interactive Mode
        js_code = read_js_file(args.script)
        config_dict = extract_config_object(js_code)
        parameters = [(param.split(':')[0], *map(float, param.split(':')[1].split(','))) for param in params_list]
    else:
        # Interactive Mode
        js_file_path = input("Enter the path to the JavaScript file: ")
        js_code = read_js_file(js_file_path)
        config_dict = extract_config_object(js_code)
        parameters = select_parameters(config_dict)

    combinations = generate_parameter_combinations(parameters)
    print_parameter_combinations(combinations)

if __name__ == "__main__":
    main()

