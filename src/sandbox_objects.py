from config import WEAVE_PROJECT

import argparse
from weave import Object
from e2b_code_interpreter import Sandbox
import weave
import os
import mimetypes
from pydantic import Field


class CodeExecutor:

    name: str = Field(default="CodeExecutor",
                      description="The name of the code executor")
    sandbox: Sandbox = Field(
        default=Sandbox(api_key=os.getenv(
            "E2B_API_KEY"), cwd="/home/user/code"), description="The sandbox to execute commands in")

    def __init__(self, name: str = "CodeExecutor"):
        super().__init__()
        self.name = name
        self.sandbox = Sandbox(api_key=os.getenv(
            "E2B_API_KEY"), cwd="/home/user/code")

    @weave.op()
    def execute(self, command: str, timeout: int = 300) -> dict:
        result = self.sandbox.process.start_and_wait(
            command,
            timeout=timeout,
            on_stderr=lambda stderr: print("[Sandbox]", stderr),
            on_stdout=lambda stdout: print("[Sandbox]", stdout),
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code
        }

    @weave.op()
    def upload_files(self, local_dir: str) -> dict:
        uploaded_files = []
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, local_dir)
                sandbox_path = f"/home/user/code/{relative_path}"

                sandbox_dir = os.path.dirname(sandbox_path)
                self.sandbox.filesystem.make_dir(sandbox_dir, timeout=None)

                if self.is_binary(local_path):
                    with open(local_path, 'rb') as file_obj:
                        content = file_obj.read()
                    self.sandbox.filesystem.write_bytes(
                        sandbox_path, content, timeout=None)
                else:
                    with open(local_path, 'r', encoding='utf-8') as file_obj:
                        content = file_obj.read()
                    content = content.replace(
                        "\\'", "'").replace('\\"', '"')
                    self.sandbox.filesystem.write(
                        sandbox_path, content, timeout=None)

                uploaded_files.append(
                    f"Uploaded: {local_path} -> {sandbox_path}")

        return {"uploaded_files": uploaded_files}

    @weave.op()
    def install_requirements(self) -> dict:
        return self.execute("pip install -r /home/user/code/requirements.txt")

    @weave.op()
    def run_tests(self) -> dict:
        return self.execute("python /home/user/code/run_tests.py")

    @weave.op()
    def run_python_code(self, code: str) -> dict:
        return self.execute(f"python -c '{code}'")

    @weave.op()
    def read_file(self, file_path: str) -> str:
        return self.sandbox.filesystem.read(file_path)

    @weave.op()
    def list_files(self, directory: str) -> list:
        return [file.name for file in self.sandbox.filesystem.list(directory)]

    def is_binary(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type and not mime_type.startswith('text')

    def close(self):
        self.sandbox.close()


class SandboxTestRunner(object):

    name: str = Field(default="SandboxTestRunner",
                      description="The name of the sandbox test runner")
    executor: CodeExecutor = Field(
        default=CodeExecutor(), description="The code executor to use")

    def __init__(self, name: str = "SandboxTestRunner"):
        super().__init__()
        self.name = name
        self.executor = CodeExecutor()

    @weave.op()
    def run_sandbox_tests(self,
                          local_dir: str = os.path.join(
                              os.getcwd(), "generated_code_20240805_103537"),
                          sandbox_dir: str = "/home/user/code",
                          requirements_file: str = "/home/user/code/requirements.txt",
                          test_script: str = "/home/user/code/run_tests.py") -> dict:
        try:
            print(f"Uploading files from local directory {local_dir}")
            upload_result = self.executor.upload_files(local_dir)
            files_list = self.executor.list_files(sandbox_dir)
            install_result = self.executor.execute(
                f"pip install -r {requirements_file}")
            test_result = self.executor.execute(f"python {test_script}")

            return {
                "uploaded_files": upload_result["uploaded_files"],
                "sandbox_files": files_list,
                "pip_install": {
                    "stdout": install_result["stdout"],
                    "stderr": install_result["stderr"]
                },
                "test_results": {
                    "stdout": test_result["stdout"],
                    "stderr": test_result["stderr"]
                }
            }
        finally:
            self.executor.close()


if __name__ == "__main__":

    weave.init(WEAVE_PROJECT)

    parser = argparse.ArgumentParser(description="Run sandbox tests")
    parser.add_argument("--local_dir", default=os.path.join(os.getcwd(), "generated_code_20240805_103537"),
                        help="Path to the local directory containing files to upload")
    parser.add_argument("--sandbox_dir", default="/home/user/code",
                        help="Path to the sandbox directory")
    parser.add_argument("--requirements_file", default="/home/user/code/requirements.txt",
                        help="Path to the requirements.txt file in the sandbox")
    parser.add_argument("--test_script", default="/home/user/code/run_tests.py",
                        help="Path to the test script in the sandbox")
    args = parser.parse_args()

    runner = SandboxTestRunner()
    result = runner.run_sandbox_tests(
        local_dir=args.local_dir,
        sandbox_dir=args.sandbox_dir,
        requirements_file=args.requirements_file,
        test_script=args.test_script
    )

    print("Uploaded files:")
    for file in result["uploaded_files"]:
        print(file)

    print(f"\nFiles in {args.sandbox_dir}:")
    print(result["sandbox_files"])

    print("\nPip install results:")
    print("Stdout:", result["pip_install"]["stdout"])
    print("Stderr:", result["pip_install"]["stderr"])

    print("\nTest results:")
    print("Stdout:", result["test_results"]["stdout"])
    print("Stderr:", result["test_results"]["stderr"])
