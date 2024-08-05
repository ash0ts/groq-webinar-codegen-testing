from sandbox_objects import CodeExecutor
from llm_models import CodeGeneratorModel, UnitTestGenerator, ProgramGeneratorModel
import weave
import asyncio
from dotenv import load_dotenv
from config import WEAVE_PROJECT
from code_types import CodeFormatter

load_dotenv()


weave.init(WEAVE_PROJECT)


@weave.op()
async def main():

    code_formatter = CodeFormatter()

    # Generate code
    prompt = """Create a simple Wordle game in Python using 3 functions:
    1. initialize_game(): Set up the game by choosing a random word from a small predefined list of 5-letter words.
    2. play_round(word, guess): Compare the guess to the word and return colored feedback using simple ASCII color codes.
    3. play_wordle(): Main game loop that handles user input, calls other functions, and limits to 6 guesses.
    
    Use minimal code and combine functionality where possible."""

    code_generator = CodeGeneratorModel()
    generated_code = code_generator.predict(prompt)
    del code_generator

    program_generator = ProgramGeneratorModel()
    program_runner = program_generator.predict(generated_code)
    del program_generator

    test_generator = UnitTestGenerator()
    unit_tests = test_generator.predict(generated_code, program_runner)
    del test_generator
    print(unit_tests)

    code_formatter.write_to_temp_folder(
        generated_code, program_runner, unit_tests)

    # Execute code
    # code_executor = CodeExecutor()
    # execution_result = code_executor.execute(full_code)

    # # Evaluate code
    # llm_judge = LLMJudge()
    # evaluation = llm_judge.evaluate(prompt, full_code, execution_result)

if __name__ == "__main__":
    asyncio.run(main())
