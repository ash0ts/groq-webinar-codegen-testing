from weave import Model
from e2b_code_interpreter import CodeInterpreter
import weave
import os


class CodeExecutor(Model):
    @weave.op()
    def execute(self, code: str) -> dict:
        with CodeInterpreter(api_key=os.getenv("E2B_API_KEY")) as code_interpreter:
            exec = code_interpreter.notebook.exec_cell(
                code,
                on_stderr=lambda stderr: print("[Code Interpreter]", stderr),
                on_stdout=lambda stdout: print("[Code Interpreter]", stdout),
            )
            return {"execution_result": exec}
