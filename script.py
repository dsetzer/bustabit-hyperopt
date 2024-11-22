import json
import logging
from py_mini_racer import MiniRacer
from typing import Tuple, Dict, Any
import hashlib

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
        self.defaults = self._convert_js_to_dict(self.config)
        # Generate script_id based on code and config structure (ignoring values)
        self.script_id = self._generate_script_id()

    @staticmethod
    def _convert_js_to_dict(obj):
        """Convert JSMappedObject to regular Python dict/list recursively"""
        if hasattr(obj, 'items'):  # JSMappedObject or dict
            return {k: Script._convert_js_to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [Script._convert_js_to_dict(item) for item in obj]
        else:
            return obj

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
        updated_config = self._convert_js_to_dict(self.config)
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
        config_code = f"var config = {json.dumps(self._convert_js_to_dict(self.config))};\n"
        return config_code + self.js_code

    def _generate_script_id(self) -> str:
        """
        Generate a unique script ID based on:
        1. The script code (excluding the config block)
        2. The config parameter structure (names and types, but not values)
        """
        # Get config structure without values
        config_structure = {
            key: {k: v for k, v in params.items() if k != 'value'}
            for key, params in self._convert_js_to_dict(self.config).items()
        }
        
        # Combine code and config structure
        unique_content = self.js_code + json.dumps(config_structure, sort_keys=True)
        return hashlib.sha256(unique_content.encode()).hexdigest()
