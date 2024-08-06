import importlib
from typing import Set
import black
from pydantic import BaseModel, Field
from typing import List

from pydantic import BaseModel, Field
from typing import List
import weave
import autopep8
import isort
from autoflake import fix_code
import os
import tempfile
from typing import List
from datetime import datetime
import ast
from pydantic import BaseModel, Field, model_validator
import sys
from stdlib_list import stdlib_list
import re


class GeneratedFunction(BaseModel):
    """Represents a single generated function with its name, implementation, and imports."""

    name: str = Field(..., description="The name of the generated function.")
    code: str = Field(..., description="The complete implementation of the function, including necessary imports at the top, followed by the function definition as a Callable.")

    @model_validator(mode='after')
    def validate_code_syntax(self) -> 'GeneratedFunction':
        code_formatter = CodeFormatter()
        formatted_code = code_formatter.lint_code(self.code)
        try:
            tree = ast.parse(formatted_code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax in code: {e}")

        # Check if there's at least one function definition
        functions = [node for node in ast.walk(
            tree) if isinstance(node, ast.FunctionDef)]
        if not functions:
            raise ValueError("No function definition found in the code")

        # Check for invalid top-level return statements
        if any(isinstance(node, ast.Return) for node in tree.body):
            raise ValueError("Invalid return statement outside of function")

        # Check if the function name matches the provided name
        if self.name not in [func.name for func in functions]:
            raise ValueError(
                f"Function named '{self.name}' not found in the code")

        return self


class GeneratedCode(BaseModel):
    """Represents the complete generated code, including multiple functions."""

    functions: List[GeneratedFunction] = Field(
        ..., description="A list of functions that solve the user's problem. All code must be in functions as Callable")


class ProgramRunner(BaseModel):
    """Contains the main function code and requirements for running the program."""

    main_function_code: str = Field(
        ..., description="The main code that orchestrates the execution of the generated functions.")

    # @model_validator(mode='after')
    # def validate_main_function_code(self) -> 'ProgramRunner':
    #     code_formatter = CodeFormatter()
    #     formatted_main_function_code = code_formatter.lint_code(
    #         self.main_function_code)
    #     try:
    #         tree = ast.parse(formatted_main_function_code)
    #     except SyntaxError as e:
    #         raise ValueError(
    #             f"Invalid Python syntax in main function code: {e}")
    #     return self


class UnitTest(BaseModel):
    """Represents a unit test for a specific generated function."""

    function_name: str = Field(
        ..., description="The name of the function for which this unit test is designed. Should match the name of a GeneratedFunction.")
    test_code: str = Field(
        ...,
        description="The complete implementation of the unittest-style test class. Ensure this is not in a markdown code block and is valid Python code."
    )

    @model_validator(mode='after')
    def validate_test_code(self) -> 'UnitTest':
        code_formatter = CodeFormatter()

        # Remove any leading/trailing whitespace and quotes
        cleaned_code = self.test_code.strip().strip('"')

        # Unescape any escaped characters
        cleaned_code = cleaned_code.encode().decode('unicode_escape')

        # Remove any triple-quote markers at the beginning and end
        cleaned_code = re.sub(r'^"""|\n?"""$', '', cleaned_code)

        formatted_test_code = code_formatter.lint_code(cleaned_code)

        # Syntax check
        try:
            tree = ast.parse(formatted_test_code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax in test code: {e}")

        # Check if the code is empty after cleaning
        if not formatted_test_code.strip():
            raise ValueError(
                "Test code is empty after removing triple-quoted blocks")

        self.test_code = formatted_test_code
        return self


class CodeFormatter(BaseModel):

    @weave.op()
    def lint_code(self, code: str) -> str:
        # Replace escaped newlines with actual newlines
        code = code.replace('\\n', '\n')

        # Parse the code to get the AST
        tree = ast.parse(code)

        # Get the set of required imports
        required_imports = self.get_required_imports(tree)

        # Generate import statements
        import_statements = self.generate_import_statements(required_imports)

        # Prepend import statements to the code
        code = import_statements + "\n\n" + code

        # Remove unused imports and variables
        code = fix_code(code, remove_all_unused_imports=True,
                        remove_unused_variables=True)

        # Sort imports
        code = isort.code(code)

        # Apply PEP 8 formatting
        code = autopep8.fix_code(code, options={'aggressive': 1})

        return code

    def get_required_imports(self, tree: ast.AST) -> Set[tuple]:
        required_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if not self.is_builtin(node.id):
                    required_imports.add((None, node.id))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        required_imports.add((node.module, alias.name))
        return required_imports

    def is_builtin(self, name: str) -> bool:
        return name in dir(__builtins__)

    def generate_import_statements(self, required_imports: Set[tuple]) -> str:
        import_statements = []
        for module, name in required_imports:
            try:
                if module:
                    importlib.import_module(module)
                    import_statements.append(f"from {module} import {name}")
                else:
                    importlib.import_module(name)
                    import_statements.append(f"import {name}")
            except ImportError:
                pass  # If the module can't be imported, skip it
        return "\n".join(import_statements)

    @weave.op()
    def format_functions(self, generated_code: GeneratedCode) -> str:
        # Format function code
        formatted_functions = "\n\n".join(
            [f.code for f in generated_code.functions])

        # Lint the combined functions
        return formatted_functions

    @weave.op()
    def format_full_code(self, generated_code: GeneratedCode, program_runner: ProgramRunner) -> str:
        functions_context = self.format_functions(generated_code)
        main_function_code = program_runner.main_function_code
        formatted_full_code = f"{functions_context}\n\n{main_function_code}"
        return self.lint_code(formatted_full_code)

    @weave.op()
    def determine_requirements(self, main_code: str) -> List[str]:
        requirements = set()
        tree = ast.parse(main_code)

        # Get the list of standard library modules for the current Python version
        std_libs = set(stdlib_list(
            f"{sys.version_info.major}.{sys.version_info.minor}"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in std_libs:
                        requirements.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] not in std_libs:
                    requirements.add(node.module.split('.')[0])

        return sorted(list(requirements))

    @weave.op()
    def write_to_temp_folder(self, generated_code: GeneratedCode, program_runner: ProgramRunner, unit_tests: List[UnitTest]) -> str:
        # temp_dir = tempfile.mkdtemp()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = f"generated_code_{timestamp}"
        package_dir = os.path.join(base_dir, "mypackage")
        os.makedirs(package_dir, exist_ok=True)

        # Write main code file
        main_code = self.format_full_code(generated_code, program_runner)
        with open(os.path.join(package_dir, "code.py"), "w") as f:
            f.write(main_code)

        # Create __init__.py in the package directory
        open(os.path.join(package_dir, "__init__.py"), "w").close()

        additional_requirements = [
            "pytest",
            "autopep8",
            "isort",
            "autoflake"
        ]
        program_requirements = self.determine_requirements(main_code)
        all_requirements = list(
            set(program_requirements + additional_requirements))
        with open(os.path.join(base_dir, "requirements.txt"), "w") as f:
            f.write("\n".join(all_requirements))

        # Create and write test files
        test_dir = os.path.join(base_dir, "tests")
        os.makedirs(test_dir)
        for i, test in enumerate(unit_tests):
            test_code = self.update_test_imports(test.test_code)
            with open(os.path.join(test_dir, f"test_{test.function_name}.py"), "w") as f:
                f.write(test_code)

        # Create __init__.py in the test directory
        open(os.path.join(test_dir, "__init__.py"), "w").close()

        # Create run_tests.py file
        run_tests_content = self.get_run_tests_content()
        with open(os.path.join(base_dir, "run_tests.py"), "w") as f:
            f.write(run_tests_content)

        # Create format_and_lint.py file
        format_and_lint_content = self.get_format_and_lint_content()
        with open(os.path.join(base_dir, "format_and_lint.py"), "w") as f:
            f.write(format_and_lint_content)

        return base_dir

    def update_test_imports(self, test_code: str) -> str:
        # Add import statement for the package at the beginning of the test file
        import_statement = "from mypackage.code import *\n\n"
        return import_statement + test_code

    def get_format_and_lint_content(self) -> str:
        return '''
import os
import autopep8
import isort
from autoflake import fix_code

def format_and_lint_file(file_path: str) -> None:
    with open(file_path, 'r') as file:
        code = file.read()

    # Remove unused imports and variables
    code = fix_code(code, remove_all_unused_imports=True, remove_unused_variables=True)

    # Sort imports
    code = isort.code(code)

    # Apply PEP 8 formatting
    code = autopep8.fix_code(code, options={'aggressive': 1})

    with open(file_path, 'w') as file:
        file.write(code)

def format_and_lint_generated_files(base_dir: str) -> None:
    # Format main code file
    main_code_path = os.path.join(base_dir, "mypackage", "code.py")
    if os.path.exists(main_code_path):
        format_and_lint_file(main_code_path)

    # Format test files
    test_dir = os.path.join(base_dir, "tests")
    if os.path.exists(test_dir):
        for file in os.listdir(test_dir):
            if file.endswith('.py'):
                file_path = os.path.join(test_dir, file)
                format_and_lint_file(file_path)

    # Format run_tests.py
    run_tests_path = os.path.join(base_dir, "run_tests.py")
    if os.path.exists(run_tests_path):
        format_and_lint_file(run_tests_path)

    print(f"Formatting and linting completed for generated files in {base_dir}")

if __name__ == "__main__":
    current_directory = os.getcwd()
    format_and_lint_generated_files(current_directory)
'''

    def get_run_tests_content(self) -> str:
        return '''
import os
import sys
import unittest

def run_tests():
    # Add the current directory to the Python path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    # Discover and run tests
    loader = unittest.TestLoader()
    test_dir = os.path.join(os.path.dirname(__file__), "tests")
    suite = loader.discover(test_dir)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return f"Tests run: {result.testsRun}, Errors: {len(result.errors)}, Failures: {len(result.failures)}"

if __name__ == "__main__":
    print(run_tests())
'''

    @weave.op()
    def format_code_and_test_output(self, generated_code: GeneratedCode, program_runner: ProgramRunner, unit_tests: List[UnitTest], execution_result: dict) -> str:
        formatted_code = self.format_full_code(generated_code, program_runner)

        # Parse the test results
        stdout = execution_result.get('stdout', '')
        stderr = execution_result.get('stderr', '')

        # Combine code, unit tests, and test results
        output = "# Generated Code\n\n```python\n"
        output += formatted_code
        output += "\n```\n\n# Unit Tests\n\n"

        for test in unit_tests:
            output += f"## Test for {test.function_name}\n\n```python\n"
            output += test.test_code
            output += "\n```\n\n"

        output += "# Test Results\n\n"

        if stdout.strip() or stderr.strip():
            output += "```\n"
            if stdout.strip():
                output += stdout.strip() + "\n\n"
            if stderr.strip():
                output += stderr.strip()
            output += "\n```\n"
        else:
            output += "No test results available. The tests may not have been executed or the results were not captured.\n\n"

        return output.strip()
