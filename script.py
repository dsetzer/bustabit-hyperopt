import json
import logging
from copy import deepcopy

import pythonmonkey as pm


class Script:
    """Represents a JavaScript file with a config object"""

    def __init__(self, file_path: str):
        """
        Initializes a Script object

        :param file_path: The path to the JavaScript file
        """
        self.js_file_path = file_path
        self.config, self.js_code = self.split_config(self.read_js_file(file_path))
        self.defaults = self.config.copy()

    @staticmethod
    def read_js_file(file_path: str) -> str:
        """
        Reads a JavaScript file and returns the raw code

        :param file_path: The path to the JavaScript file
        :return: The raw code of the JavaScript file
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def object_to_dict(self, js_object):
        """
        Converts a JSObject to a Python dictionary

        :param js_object: The JSObject to convert
        :return: A Python dictionary with the same keys and values as the JSObject
        """
        return {key: self.object_to_dict(value) if isinstance(value, dict) else value for key, value in js_object.items()}

    def dict_to_object(self, py_dict: dict) -> str:
        """
        Converts a Python dictionary to a JavaScript object string

        :param py_dict: The Python dictionary to convert
        :return: A string representation of the JavaScript object
        """
        return "{ " + ", ".join([f"{key}: {self.dict_to_object(value)}" if isinstance(value, dict) else f"{key}: {json.dumps(value)}" for key, value in py_dict.items()]) + " }"

    def split_config(self, raw_js_code: str):
        """
        Parses the script contents and splits the config object from the rest of the script

        :param raw_js_code: The raw script code
        :return: A tuple of the config object and the remaining script code
        """
        start_index = raw_js_code.find('var config = {')
        if start_index == -1:
            raise FileNotFoundError("Config object not found")

        end_index = start_index
        brace_count = 0
        for i, char in enumerate(raw_js_code[start_index:]):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_index = start_index + i
                    break

        # Move the end index to the next character after any whitespace or semicolons
        for i, char in enumerate(raw_js_code[end_index + 1:]):
            if char.strip():  # Stop at the first non-whitespace character
                if char == ';':
                    end_index += i + 1
                break

        # Extract and evaluate only the config object definition
        config_code = raw_js_code[start_index:end_index + 1]
        remaining_code = raw_js_code[:start_index] + raw_js_code[end_index + 1:]

        pm.eval(config_code)
        config_object = pm.globalThis.config
        # config = self.object_to_dict(config_object)

        return config_object, remaining_code

    def get_config(self, new_values: dict):
        """
        Returns a config object with the given parameters set to the given values

        :param new_values: A dictionary of parameter names and values to set
        :return: A config object with the given parameters set to the given values
        """
        updated_config = deepcopy(self.config)
        for key, value in new_values.items():
            if key not in updated_config:
                raise KeyError(f"Parameter {key} not found in config")
            if updated_config[key]['type'] == 'balance':
                updated_config[key]['value'] = int(float(value)) * 100
            else:
                updated_config[key]['value'] = value
        return updated_config

    def merge_config(self):
        """
        Returns the full script code with the config object merged in

        :return: The full script code with the config object merged in
        """
        config_code = "var config = {\n"
        for key, item in self.config.items():
            config_code += f"    {key}: {self.dict_to_object(item)},\n"
        config_code += "};\n"

        return config_code + self.js_code

