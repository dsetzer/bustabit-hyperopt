import asyncio
from datetime import datetime
import os

from prettytable import PrettyTable

from script import Script
from simulator import GameResults, Simulator


def get_input(prompt):
    return input(prompt).strip()

def get_float_input(prompt):
    while True:
        try:
            value = float(get_input(prompt))
            return value
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_int_input(prompt):
    while True:
        try:
            value = int(get_input(prompt))
            return value
        except ValueError:
            print("Invalid input. Please enter an integer.")

def print_results(results):
    table = PrettyTable()
    table.field_names = ["Statistic", "Value"]
    for key, value in results.items():
        table.add_row([key, value])
    print(table)
    
def main():
    script_path = get_input("Enter the path to the script: ")
    hash_value = get_input("Enter the hash value: ")
    num_games = get_int_input("Enter the number of games to generate: ")
    initial_balance = get_float_input("Enter the initial balance: ")

    script = Script(script_path)
    simulator = Simulator(script)
    game_results = GameResults(1.98, 1, num_games)

    # Create folder with script file name and datetime
    script_name = os.path.basename(script_path)
    folder_name = f"{script_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(folder_name)

    # Save simulation results to a file
    results_file_path = os.path.join(folder_name, "results.txt")
    with open(results_file_path, "w") as results_file:
        loop = asyncio.get_event_loop()
        simulation_task = loop.create_task(simulator.run(initial_balance, game_results, {}))

        try:
            loop.run_until_complete(simulation_task)
            results = simulation_task.result()
            results_file.write(str(results["results"]))
        except Exception as e:
            results_file.write(f"Error occurred: {str(e)}")

    # Copy script to the folder
    script_copy_path = os.path.join(folder_name, script_name)
    os.system(f"cp {script_path} {script_copy_path}")

    # Save script log output to a file
    log_file_path = os.path.join(folder_name, "log.txt")
    with open(log_file_path, "w") as log_file:
        log_file.write("\n".join(results["output"]))

    print(f"Simulation results, script copy, and log output saved in folder: {folder_name}")

if __name__ == "__main__":
    main()