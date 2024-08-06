import re
from typing import Dict, Any, Optional
from weave import Model, Scorer
import weave


class TestResultScorer(Scorer):
    @weave.op()
    def parse_test_results(self, test_output: str) -> Dict[str, int]:
        # Extract the summary line
        summary_match = re.search(
            r"Tests run: (\d+), Errors: (\d+), Failures: (\d+)", test_output)
        if not summary_match:
            return {"error": "Could not parse test summary"}

        tests_run = int(summary_match.group(1))
        errors = int(summary_match.group(2))
        failures = int(summary_match.group(3))

        # Calculate passed tests
        passed = tests_run - (errors + failures)

        return {
            "tests_run": tests_run,
            "passed": passed,
            "errors": errors,
            "failures": failures
        }

    @weave.op()
    def score(self, model_output: Optional[Dict[str, Any]], prompt: str) -> Dict[str, Any]:
        if model_output is None or "execution_result" not in model_output:
            return {"error": "No execution result provided in model output"}

        execution_result = model_output["execution_result"]
        test_output = execution_result.get(
            "stdout", "") + "\n" + execution_result.get("stderr", "")

        return self.parse_test_results(test_output)
