# pylint: disable=import-error, missing-function-docstring, missing-class-docstring, missing-module-docstring
from STPyV8 import JSContext, JSObject

class Script:
    def __init__(self, file_path):
        self.js_code = self.read_js_file(file_path)
        self.config_dict = self.extract_config_object()

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

    def extract_config_object(self):
        start_index = self.js_code.find('var config = {')
        if start_index == -1:
            raise FileNotFoundError("Config object not found")

        end_index = start_index
        brace_count = 0
        for i, char in enumerate(self.js_code[start_index:]):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_index = start_index + i
                    break

        # Extract and evaluate only the config object definition
        config_code = self.js_code[start_index:end_index + 1]

        with JSContext() as ctxt:
            ctxt.eval(config_code)
            config_object = ctxt.eval("config")
            config_dict = self.js_object_to_python(config_object)

        return config_dict