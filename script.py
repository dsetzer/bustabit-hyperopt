# pylint: disable=import-error, missing-function-docstring, missing-class-docstring, missing-module-docstring
import STPyV8 as V8
import json
import logging

class Script:
    def __init__(self, file_path):
        self.js_file_path = file_path
        logging.info(f"Initializing script with file: {file_path}")
        raw_js_code = self.read_js_file(file_path)
        self.config_dict, self.js_code = self.split_config(raw_js_code)

    @staticmethod
    def read_js_file(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            js_code = file.read()
        return js_code

    def object_to_dict(self, js_obj):
        python_dict = {}
        for key in js_obj.keys():
            value = js_obj[key]
            if isinstance(value, V8.JSObject):
                python_dict[key] = self.object_to_dict(value)
            else:
                python_dict[key] = value
        return python_dict
    
    def dict_to_object(self, py_dict):
        items = [f'{k}: {json.dumps(v)}' if not isinstance(v, dict) else f'{k}: {self.dict_to_object(v)}' for k, v in py_dict.items()]
        return "{ " + ", ".join(items) + " }"

    def split_config(self, raw_js_code):
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

        with V8.JSContext() as ctxt:
            ctxt.eval(config_code)
            config_object = ctxt.eval("config")
            config_dict = self.object_to_dict(config_object)

        return config_dict, remaining_code

    def set_params(self, **params):
        logging.info(f"Setting parameters: {params}")
        for key, value in params.items():
            if key in self.config_dict:
                if self.config_dict[key]['type'] == 'balance':
                    self.config_dict[key]['value'] = int(float(value)) * 100
                else:
                    self.config_dict[key]['value'] = value
            else:
                raise KeyError(f"Parameter {key} not found in config")
    def merge_config(self):
        # build a string of the config object definition with each item on a new line and defined as a var object.
        config_code = "var config = {\n"
        for key, item in self.config_dict.items():
            config_code += f"    {key}: {self.dict_to_object(item)},\n"
        config_code += "};\n"

        # Combine the config code with the remaining js code
        combined_code = config_code + self.js_code

        return combined_code
