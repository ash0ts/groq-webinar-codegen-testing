from typing import Dict, Any, Optional
from weave.flow.scorer import Scorer
from weave import Model, Scorer
from groq import Groq
import instructor
from code_types import GeneratedCode, GeneratedFunction, UnitTest, ProgramRunner, CodeFormatter
from eval_types import CodeEvaluation
from typing import List, Dict, Any
import os
import weave
import autopep8
import isort
from autoflake import fix_code
from llm_utils import generate_with_retry
from typing import Optional
from config import SEEDS


class CodeGeneratorModel(Model):
    model_name: str = "llama3-groq-70b-8192-tool-use-preview"
    system_prompt: str = """You are an expert Python code generator. Adhere to these guidelines:

1. Use type hints for all function parameters and return values.
2. Optimize for O(n) time complexity or better where possible.
3. Use list/dict comprehensions and generator expressions for concise data processing.
4. Leverage `collections` module for efficient data structures (e.g., defaultdict, Counter).
5. Use f-strings for string formatting.
6. Ensure all functions are properly defined and indented.
7. Don't include any code outside of function definitions.
8. Use meaningful variable names and add brief comments for clarity.
9. Handle potential errors and edge cases.
10. Follow PEP 8 style guidelines for consistent and readable code.
11. In the requirements section, only list external packages that need to be installed via pip. Do not include built-in Python modules."""

    @weave.op()
    def predict(self, prompt: str, use_seed: bool = True, seed: Optional[int] = None) -> str:
        generated_code = self.generate_code(prompt, use_seed, seed)
        return generated_code

    @weave.op()
    def generate_code(self, prompt: str, use_seed: bool = True, seed: Optional[int] = None) -> GeneratedCode:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return generate_with_retry(
            model_name=self.model_name,
            messages=messages,
            response_model=GeneratedCode,
            use_seed=use_seed,
            seed=seed,
        )


class ProgramGeneratorModel(Model):
    model_name: str = "llama3-groq-70b-8192-tool-use-preview"
    system_prompt: str = """You are an expert Python program generator. Create a main function that orchestrates the execution of the given functions. Follow these guidelines:

1. Create a main() function that calls the necessary functions to run the program.
2. Include a proper if __name__ == "__main__": guard to call the main() function.
3. Do not redefine or implement any functions; use only the functions provided.
4. Do not include any imports or package specifications.
5. Use clear and concise code with proper indentation.
6. Do not use escape characters for newlines; write actual line breaks.
7. Keep the main() function simple, calling only the top-level function(s) needed.

Example structure:

def main():
    result = top_level_function()
    print(result)

if __name__ == "__main__":
    main()

Remember, your task is solely to create the main() function and the __main__ guard. All other functions are assumed to be already defined."""
    context_prompt: str = """
Generate a minimal main function that only calls the necessary function(s) to run the program. The following functions have already been defined:

{functions_context}

Requirements:
1. The main function should ONLY call the top-level function(s) needed to run the program.
2. Do NOT redefine any functions or include any imports within main.
3. Do NOT include any logic other than calling the necessary function(s).
4. Assume all required setup and initialization is done within the called function(s).
5. Use proper indentation and formatting.
6. Do NOT use escape characters like \\n for newlines. Write the code as you normally would, with actual line breaks.

Example of what we're looking for:

def main():
    play_wordle()  # Or whatever the top-level function is named

if __name__ == "__main__":
    main()
"""
    code_formatter: CodeFormatter = CodeFormatter()

    @weave.op()
    def generate_program(self, generated_code: GeneratedCode, use_seed: bool = True, seed: Optional[int] = None) -> ProgramRunner:
        functions_context = self.code_formatter.lint_code(
            self.code_formatter.format_functions(generated_code))

        prompt = self.context_prompt.format(
            functions_context=functions_context)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return generate_with_retry(
            model_name=self.model_name,
            messages=messages,
            response_model=ProgramRunner,
            use_seed=use_seed,
            seed=seed
        )

    @weave.op()
    def predict(self, generated_code: GeneratedCode, use_seed: bool = True, seed: Optional[int] = None) -> ProgramRunner:
        return self.generate_program(generated_code, use_seed, seed)


class UnitTestGenerator(Model):
    model_name: str = "llama-3.1-8b-instant"
    system_prompt: str = """You are an expert Python unit test generator. Your task is to create comprehensive, isolated, and efficient unittest-style tests that adhere to best practices. Ensure proper formatting, complete test classes, and consider all possible scenarios including edge cases and potential errors."""

    unit_test_prompt_template: str = """
Generate a complete unittest for the following function:

```python
{func.code}
```

Context (Surrounding Code):
```python
{formatted_full_code}
```

Requirements:

1. **Structure:** Use `unittest.TestCase` and name the class `Test<FunctionName>`.
2. **Coverage:** Include tests for normal cases, edge cases, and potential errors.
3. **Naming:** Use descriptive test method names (e.g., `test_valid_input`, `test_empty_input`, `test_invalid_input_type`).
4. **Type Hints:** Include type hints for clarity.
5. **Mocking:** Mock external dependencies (e.g., database interactions, API calls) when necessary.
6. **Assertions:** Use appropriate assertions (e.g., `assertEqual`, `assertRaises`, `assertTrue`).
7. **Isolation:** Ensure test isolation to prevent interference between tests.
9. **Executable:** Include a `__main__` block to run tests directly: `if __name__ == '__main__': unittest.main()`
10. **Formatting:** Ensure proper indentation and formatting for readability.
11. **Imports:** Include all necessary imports.
12. **Completeness:** Provide a complete, runnable test file.

**Example:**

Let's say the provided function is:

```python
def add(x: int, y: int) -> int:
  # Adds two integers together
  return x + y
```

A good unit test might look like:

```python
import unittest

class TestAdd(unittest.TestCase):

    def test_positive_numbers(self):
        # Test adding two positive numbers
        self.assertEqual(add(2, 3), 5)

    def test_zero(self):
        # Test adding zero
        self.assertEqual(add(5, 0), 5)

    def test_negative_numbers(self):
        # Test adding negative numbers
        self.assertEqual(add(-2, -3), -5)

if __name__ == '__main__':
    unittest.main()
```

**Now, generate the unit test for the given function based on the context and requirements above.**

Provide only the complete, properly formatted test code, no explanations or markdown.
"""

    code_formatter: CodeFormatter = CodeFormatter()

    @weave.op()
    def generate_test(self, formatted_full_code: str, func: GeneratedFunction, use_seed: bool = True, seed: Optional[int] = None) -> UnitTest:
        prompt = self.unit_test_prompt_template.format(
            formatted_full_code=formatted_full_code,
            func=func
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return generate_with_retry(
            model_name=self.model_name,
            messages=messages,
            response_model=UnitTest,
            use_seed=use_seed,
            seed=seed
        )

    @weave.op()
    def generate_tests(self, generated_code: GeneratedCode, program_runner: ProgramRunner, use_seed: bool = True, seeds: Optional[List[int]] = None) -> List[UnitTest]:
        formatted_full_code = self.code_formatter.format_full_code(
            generated_code, program_runner)
        tests = []

        for i, func in enumerate(generated_code.functions):
            seed = seeds[i] if use_seed and seeds and i < len(seeds) else None
            try:
                test = self.generate_test(
                    formatted_full_code, func, use_seed, seed)
                tests.append(test)
            except Exception as e:
                # Log the error or handle it as needed
                continue

        return tests

    @weave.op()
    def predict(self, generated_code: GeneratedCode, program_runner: ProgramRunner, use_seed: bool = True, seeds: Optional[List[int]] = None) -> List[UnitTest]:
        return self.generate_tests(generated_code, program_runner, use_seed, seeds)


class LLMJudge(Scorer):
    model_name: str = "llama-3.1-8b-instant"
    system_prompt: str = "You are an expert code reviewer. Evaluate the given code based on the provided criteria. Be objective and thorough in your assessment."
    evaluation_prompt_template: str = """
        Evaluate the following code implementation:

        {full_code}

        Given the prompt:

        {prompt}

        Evaluate the generated code based on the following criteria. For each criterion, provide a score from 1 to 10 (where 1 is poor and 10 is excellent) and a brief, specific explanation for your score.

        1. Functional Correctness: Does the code correctly solve the intended problem? Consider the test results.
        Score: [1-10]
        Explanation: [Provide a concise explanation]

        2. Code Quality: Is the code readable, efficient, and adhering to best practices?
        Score: [1-10]
        Explanation: [Provide a concise explanation]

        3. Test Coverage: How comprehensive are the unit tests? Do they cover various scenarios and edge cases?
        Score: [1-10]
        Explanation: [Provide a concise explanation]

        4. Error Handling: Does the code handle potential errors and edge cases appropriately?
        Score: [1-10]
        Explanation: [Provide a concise explanation]

        5. Overall Implementation: Considering the code, tests, and test results, how well does this solution meet the requirements?
        Score: [1-10]
        Explanation: [Provide a concise explanation]

        Overall Score: [1-10]
        Overall Explanation: [Provide a concise summary of the code's strengths and weaknesses, including suggestions for improvement]
        """

    @weave.op()
    def evaluate(self, full_code: str, prompt: str) -> Dict[str, Any]:
        evaluation_prompt = self.evaluation_prompt_template.format(
            full_code=full_code,
            prompt=prompt
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": evaluation_prompt}
        ]
        evaluation = generate_with_retry(
            model_name=self.model_name,
            messages=messages,
            response_model=CodeEvaluation
        )

        return evaluation

    @weave.op()
    def score(self, model_output: Optional[Dict[str, Any]], prompt: str) -> Dict[str, Any]:
        if model_output is None or "full_code" not in model_output:
            return {"error": "No model output provided"}

        full_code = model_output.get("full_code")
        if not full_code:
            return {"error": "No code provided in model output"}

        evaluation = self.evaluate(full_code, prompt)
        formatted_evaluation = {
            "functional_correctness": evaluation.functional_correctness.score,
            "code_quality": evaluation.code_quality.score,
            "generalization": evaluation.generalization.score,
            "consistency": evaluation.consistency.score,
            "error_handling": evaluation.error_handling.score,
            "overall": evaluation.overall.score
        }
        return formatted_evaluation
