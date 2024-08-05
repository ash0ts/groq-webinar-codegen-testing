from weave import Model
from groq import Groq
import instructor
from code_types import GeneratedCode, GeneratedFunction, UnitTest, ProgramRunner, CodeFormatter
from eval_types import CodeEvaluation
from typing import List
import os
import weave
import autopep8
import isort
from autoflake import fix_code
from config import SEED


class CodeGeneratorModel(Model):
    model_name: str = "mixtral-8x7b-32768"
    system_prompt: str = """You are an expert Python code generator. Adhere to these guidelines:

1. Use type hints for all function parameters and return values.
2. Optimize for O(n) time complexity or better where possible.
3. Use list/dict comprehensions and generator expressions for concise data processing.
4. Leverage `collections` module for efficient data structures (e.g., defaultdict, Counter).
5. Use f-strings for string formatting."""

    @weave.op()
    def predict(self, prompt: str) -> str:
        generated_code = self.generate_code(prompt)
        return generated_code

    @weave.op()
    def generate_code(self, prompt: str) -> GeneratedCode:
        client: instructor.Instructor = instructor.from_groq(
            Groq(api_key=os.getenv("GROQ_API_KEY")), mode=instructor.Mode.TOOLS)
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_model=GeneratedCode,
            max_retries=10,
        )
        return response


class ProgramGeneratorModel(Model):
    model_name: str = "mixtral-8x7b-32768"
    system_prompt: str = """You are an expert Python program generator. Create a main function that orchestrates the execution of the given functions and specify any required packages. Follow these guidelines:

1. Use type hints and follow PEP 8 style.
2. Optimize for performance and readability.
3. Include necessary imports and specify external dependencies.
4. Use consistent naming and provide brief docstrings.
5. Handle errors and edge cases appropriately.
6. Avoid redundancy and unnecessary code."""
    code_formatter: CodeFormatter = CodeFormatter()

    @weave.op()
    def generate_program(self, generated_code: GeneratedCode) -> ProgramRunner:
        client: instructor.Instructor = instructor.from_groq(
            Groq(api_key=os.getenv("GROQ_API_KEY")), mode=instructor.Mode.TOOLS)

        functions_context = self.code_formatter.lint_code(
            self.code_formatter.format_functions(generated_code))

        prompt = f"""
        Generate a minimal main function that only calls the necessary function(s) to run the program. The following functions have already been defined:

        {functions_context}

        Requirements:
        1. The main function should ONLY call the top-level function(s) needed to run the program.
        2. Do NOT redefine any functions or include any imports within main.
        3. Do NOT include any logic other than calling the necessary function(s).
        4. Assume all required setup and initialization is done within the called function(s).

        Example of what we're looking for:

        def main():
            play_wordle()  # Or whatever the top-level function is named

        if __name__ == "__main__":
            main()
        """

        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_model=ProgramRunner,
            max_retries=10,
        )
        return response

    @weave.op()
    def predict(self, generated_code: GeneratedCode) -> ProgramRunner:
        return self.generate_program(generated_code)


class UnitTestGenerator(Model):
    model_name: str = "mixtral-8x7b-32768"
    system_prompt: str = """Generate pytest-style unit tests following these key rules:
1. Prefix test functions with 'test_'
2. Use descriptive names with underscores (e.g., test_valid_input)
3. Include necessary imports at the top
4. Use assert statements for validations
5. Add type hints to test functions"""

    unit_test_prompt_template: str = """
        Generate a pytest-style unit test for a function within the following program implementation:

        ```python
        {formatted_full_code}
        ```

        The specific function to test is:
        ```python
        {func.code}
        ```

        Please create a comprehensive test that:
        1. Covers various scenarios, including edge cases and typical use cases.
        2. Considers the context of the entire program, including how this function interacts with others.
        3. Mocks any external dependencies or random functions if necessary.
        4. Uses pytest fixtures for setup and teardown if appropriate.
        5. Ensures the test is isolated and doesn't depend on the state of other tests.
        6. Uses meaningful test data that reflects real-world usage of the function.

        The test should be in the format of a Python function named 'test_<function_name>'.
        Include any necessary imports for the test function.
        """
    code_formatter: CodeFormatter = CodeFormatter()

    @weave.op()
    def generate_test(self, formatted_full_code: str, func: GeneratedFunction) -> UnitTest:
        client: instructor.Instructor = instructor.from_groq(
            Groq(api_key=os.getenv("GROQ_API_KEY")), mode=instructor.Mode.TOOLS)
        prompt = self.unit_test_prompt_template.format(
            formatted_full_code=formatted_full_code,
            func=func
        )
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_model=UnitTest,
            max_retries=10,
        )
        return response

    @weave.op()
    def generate_tests(self, generated_code: GeneratedCode, program_runner: ProgramRunner) -> List[UnitTest]:
        tests = []
        formatted_full_code = self.code_formatter.format_full_code(
            generated_code, program_runner)
        for func in generated_code.functions:
            test = self.generate_test(
                formatted_full_code, func)
            tests.append(test)

        return tests

    @weave.op()
    def predict(self, generated_code: GeneratedCode, program_runner: ProgramRunner) -> List[UnitTest]:
        return self.generate_tests(generated_code, program_runner)


class LLMJudge(Model):

    model_name: str = "llama-3.1-8b-instant"
    system_prompt: str = "You are an expert code reviewer. Evaluate the given code based on the provided criteria."
    evaluation_prompt_template: str = """
        Prompt: {prompt}
        Generated Code:
        ```python
        {generated_code}
        ```
        Execution Result:
            Result: {execution_result['execution_result'].results}
            Stdout: {execution_result['execution_result'].logs.stdout}
            Stderr: {execution_result['execution_result'].logs.stderr}
            Error: {execution_result['execution_result'].error}
        Evaluate the generated code based on the following criteria:
        1. Correctness: Does the code correctly implement the requested functionality?
        2. Efficiency: Is the code implemented efficiently?
        3. Readability: Is the code easy to read and understand?
        4. Error Handling: Does the code handle potential errors appropriately?

        Provide a score for each criterion (1-10) and an overall score (1-10), along with a brief explanation.
        """

    @weave.op()
    def evaluate(self, prompt: str, generated_code: str, execution_result: dict) -> CodeEvaluation:
        client: instructor.Instructor = instructor.from_groq(
            Groq(api_key=os.getenv("GROQ_API_KEY")), mode=instructor.Mode.TOOLS, seed=SEED)
        evaluation_prompt = self.evaluation_prompt_template.format(
            prompt=prompt,
            generated_code=generated_code,
            execution_result=execution_result
        )
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": evaluation_prompt}
            ],
            response_model=CodeEvaluation,
            max_retries=10,
        )
        return response
