from pydantic import BaseModel, Field
from typing import List

from pydantic import BaseModel, Field
from typing import List
import weave
import autopep8
import isort
from autoflake import fix_code


class GeneratedFunction(BaseModel):
    """Represents a single generated function with its name, implementation, and imports."""

    name: str = Field(..., description="The name of the generated function.")
    code: str = Field(..., description="The complete implementation of the function, including necessary imports at the top, followed by the function definition.")


class GeneratedCode(BaseModel):
    """Represents the complete generated code, including multiple functions."""

    functions: List[GeneratedFunction] = Field(
        ..., description="A list of functions that solve the user's problem.")


class ProgramRunner(BaseModel):
    """Contains the main function code and requirements for running the program."""

    main_function_code: str = Field(
        ..., description="The main code that orchestrates the execution of the generated functions.")
    requirements: List[str] = Field(
        ..., description="List of package requirements based on imports from all functions.")


class UnitTest(BaseModel):
    """Represents a unit test for a specific generated function."""

    function_name: str = Field(
        ..., description="The name of the function for which this unit test is designed. Should match the name of a GeneratedFunction.")
    test_code: str = Field(..., description="The complete implementation of the unit test, including test setup, assertions, and any necessary imports or fixtures.")


class CodeFormatter(BaseModel):

    @weave.op()
    def lint_code(self, code: str) -> str:
        # Remove unused imports and variables
        code = fix_code(code, remove_all_unused_imports=True,
                        remove_unused_variables=True)

        # Sort imports
        code = isort.code(code)

        # Apply PEP 8 formatting
        code = autopep8.fix_code(code, options={'aggressive': 1})

        return code

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
