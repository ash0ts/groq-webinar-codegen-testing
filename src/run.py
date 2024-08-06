import weave
from weave import Dataset, Evaluation
from config import WEAVE_PROJECT, MODELS
from sandbox_objects import SandboxTestRunner
from llm_models import CodeGeneratorModel, UnitTestGenerator, ProgramGeneratorModel, LLMJudge
from code_types import CodeFormatter
from scorers import TestResultScorer
import asyncio

weave.init(WEAVE_PROJECT)


class CodeGenerationPipeline(weave.Model):

    code_formatter: CodeFormatter = None
    code_generator: CodeGeneratorModel = None
    program_generator: ProgramGeneratorModel = None
    test_generator: UnitTestGenerator = None
    test_runner: SandboxTestRunner = None
    llm_judge: LLMJudge = None

    def __init__(self, model_name: str = "llama3-groq-70b-8192-tool-use-preview"):
        super().__init__()
        self.code_formatter = CodeFormatter()
        self.code_generator = CodeGeneratorModel()
        self.program_generator = ProgramGeneratorModel()
        self.test_generator = UnitTestGenerator(model_name=model_name)
        self.test_runner = SandboxTestRunner()

    @weave.op()
    async def predict(self, prompt: str):
        print("Generating code")
        generated_code = self.code_generator.predict(prompt, seed=724239)

        print("Generating program")
        program_runner = self.program_generator.predict(
            generated_code, seed=274136)

        print("Generating unit tests")
        unit_tests = self.test_generator.predict(
            generated_code, program_runner,
            # seeds=[205048, 205048]
        )

        print("Writing to temp folder")
        temp_folder = self.code_formatter.write_to_temp_folder(
            generated_code, program_runner, unit_tests)

        print("Running tests")
        execution_result = self.test_runner.run_sandbox_tests(temp_folder)[
            'test_results']
        full_code = self.code_formatter.format_code_and_test_output(
            generated_code, program_runner, unit_tests, execution_result)

        return {
            "generated_code": generated_code,
            "program_runner": program_runner,
            "unit_tests": unit_tests,
            "execution_result": execution_result,
            "full_code": full_code
        }


@weave.op()
async def main():
    # Create a dataset with the prompt
    prompt_dataset = Dataset(name="stock_market_data_processing_prompt", rows=[
        {
            "prompt": """Create two Python functions for processing streaming stock market data:

            1. parse_trade(trade_data: str) -> dict:
               - Takes a string of comma-separated trade data: "symbol,price,quantity,timestamp"
               - Returns a dictionary with keys 'symbol', 'price' (float), 'quantity' (int), and 'timestamp' (datetime object)
               - Skips invalid trades (e.g., missing fields, non-numeric price/quantity)

            2. calculate_vwap(trades: list[dict]) -> dict:
               - Takes a list of parsed trade dictionaries
               - Calculates the Volume Weighted Average Price (VWAP) for each symbol
               - Returns a dictionary with symbols as keys and their VWAP as values

            Ensure the functions are efficient and handle potential errors. Keep the code concise and easily unit-testable."""
        }
    ])

    # Publish the dataset
    weave.publish(prompt_dataset)

    # Create the pipeline model
    for model_name in MODELS:
        pipeline = CodeGenerationPipeline(model_name=model_name)

        # Create the LLMJudge scorer
        llm_judge = LLMJudge()

        # Create the test result scorer
        test_result_scorer = TestResultScorer()

        # Create the evaluation
        evaluation = Evaluation(
            name="code_generation_evaluation",
            dataset=prompt_dataset,
            scorers=[llm_judge, test_result_scorer]
        )

        # Run the evaluation
        results = await evaluation.evaluate(pipeline)
        print(results)

if __name__ == "__main__":
    asyncio.run(main())
