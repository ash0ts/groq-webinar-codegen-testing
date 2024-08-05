from sandbox_objects import CodeExecutor
from llm_models import CodeGeneratorModel, UnitTestGenerator, ProgramGeneratorModel
import weave
import asyncio
from dotenv import load_dotenv
from config import WEAVE_PROJECT

load_dotenv()


weave.init(WEAVE_PROJECT)


@weave.op()
async def main():
    # Initialize models
    # code_executor = CodeExecutor()
    # llm_judge = LLMJudge()

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

    # Execute code
    # execution_result = code_executor.execute(full_code)

    # # Evaluate code
    # evaluation = llm_judge.evaluate(prompt, full_code, execution_result)

if __name__ == "__main__":
    asyncio.run(main())
