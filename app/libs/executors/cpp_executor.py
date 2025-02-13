from contextlib import contextmanager
import tempfile
from typing import Any, Generator
from app.libs.executors.executor import COMPILE_ERROR_EXIT_CODE, ProcessExecuteResult, ScriptExecutor, CompileError


class CppExecutor(ScriptExecutor):
    def __init__(self, compiler_path: str):
        self.compiler_path = compiler_path
        # TODO: add timeout/memory limit support

    @contextmanager
    def setup_command(self, script: str) -> Generator[list[str], Any, None]:
        with tempfile.TemporaryDirectory() as tmp_path:
            source_path = f"{tmp_path}/source.cpp"
            exec_path = f"{tmp_path}/run"
            with open(source_path, "w") as f:
                f.write(script)
            result = self.execute({'args': [self.compiler_path,  "-O2", source_path,  "-o", exec_path]})
            if not result.success:
                raise CompileError(result.stderr)
            yield [exec_path]

    def execute_script(self, script, stdin=None, timeout=None):
        try:
            return super().execute_script(script, stdin, timeout)
        except CompileError as e:
            return ProcessExecuteResult(stdout='', stderr=str(e), exit_code=COMPILE_ERROR_EXIT_CODE, cost=0)
