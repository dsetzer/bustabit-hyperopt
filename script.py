import json
import logging
from py_mini_racer import MiniRacer
from typing import Tuple, Dict, Any

class Script:
    """Represents a JavaScript file with a config object"""

    def __init__(self, file_path: str):
        """
        Initializes a Script object

        :param file_path: The path to the JavaScript file
        """
        self.js_file_path = file_path
        self.raw_js_code = self.read_js_file(file_path)
        self.config, self.js_code = self.split_config(self.raw_js_code)
        self.defaults = self.deep_copy_config(self.config)

    @staticmethod
    def read_js_file(file_path: str) -> str:
        """
        Reads a JavaScript file and returns the raw code

        :param file_path: The path to the JavaScript file
        :return: The raw code of the JavaScript file
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def split_config(self, raw_js_code: str) -> Tuple[Dict[str, Any], str]:
        """
        Parses the script contents and splits the config object from the rest of the script

        :param raw_js_code: The raw script code
        :return: A tuple of the config object and the remaining script code
        """
        start_index = raw_js_code.find('var config = {')
        if start_index == -1:
            raise ValueError("Config object not found in the script")

        end_index = raw_js_code.find('};', start_index) + 1
        if end_index == -1:
            raise ValueError("Invalid config object in the script")

        config_code = raw_js_code[start_index:end_index + 1]
        remaining_code = raw_js_code[:start_index] + raw_js_code[end_index + 1:]

        # Evaluate the config object using py_mini_racer
        ctx = MiniRacer()
        ctx.eval(config_code)
        config_object = ctx.eval('config')

        return config_object, remaining_code

    def deep_copy_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a deep copy of the config object

        :param config: The config object to copy
        :return: A deep copy of the config object
        """
        return json.loads(json.dumps(config))

    def get_config(self, new_values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a config object with the given parameters set to the given values

        :param new_values: A dictionary of parameter names and values to set
        :return: A config object with the given parameters set to the given values
        """
        updated_config = self.deep_copy_config(self.config)
        for key, value in new_values.items():
            if key not in updated_config:
                raise KeyError(f"Parameter {key} not found in config")
            if updated_config[key]['type'] == 'balance':
                updated_config[key]['value'] = int(float(value) * 100)
            else:
                updated_config[key]['value'] = value
        return updated_config

    def merge_config(self) -> str:
        """
        Returns the full script code with the config object merged in

        :return: The full script code with the config object merged in
        """
        config_code = f"var config = {json.dumps(self.config)};\n"
        return config_code + self.js_code

    def generate_id(self, new_values: dict):
        """Generates an id from a set of configuration parameter values

        :param new_values: A dictionary of parameter names and values to set
        :return: A string representation of the id
        """
        updated_config = self.get_config(new_values)
        config_str = json.dumps(updated_config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()
