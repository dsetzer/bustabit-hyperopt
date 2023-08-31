# pylint: disable=import-error, missing-function-docstring, missing-class-docstring, missing-module-docstring
from STPyV8 import JSContext, JSObject

class Script:
    def __init__(self, file_path):
        raw_js_code = self.read_js_file(file_path)
        self.config_dict, self.js_code = self.split_config(raw_js_code)

    @staticmethod
    def read_js_file(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            js_code = file.read()
        return js_code

    def js_object_to_python(self, js_obj):
        python_dict = {}
        for key in js_obj.keys():
            value = js_obj[key]
            if isinstance(value, JSObject):
                python_dict[key] = self.js_object_to_python(value)
            else:
                python_dict[key] = value
        return python_dict

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

        with JSContext() as ctxt:
            ctxt.eval(config_code)
            config_object = ctxt.eval("config")
            config_dict = self.js_object_to_python(config_object)

        return config_dict, remaining_code


    def get_config_js_code(self):
        # build a string of the config object definition with each item on a new line and defined as a var object.
        config_code = "var config = {\n"
        for key in self.config_dict.keys():
            config_code += f"    {key}: {self.config_dict[key]},\n"
        config_code += "};\n"
        return config_code

    def get_combined_js_code(self):
        return self.get_config_js_code() + self.js_code