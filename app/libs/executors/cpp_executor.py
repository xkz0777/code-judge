from contextlib import contextmanager
import tempfile
from typing import Any, Generator
from app.libs.executors.executor import (
    execute,
    COMPILE_ERROR_EXIT_CODE, ProcessExecuteResult, ScriptExecutor, CompileError
)


INIT_TEMPLATE = """
""".strip()


class CppExecutor(ScriptExecutor):
    def __init__(self, compiler_path: str, timeout: int | None = None, max_memory: int | None = None):
        super().__init__(timeout, max_memory)
        self.compiler_path = compiler_path

    @contextmanager
    def setup_command(self, script: str) -> Generator[list[str], Any, None]:
        with tempfile.TemporaryDirectory() as tmp_path:
            source_path = f"{tmp_path}/source.cpp"
            init_header_path = f"{tmp_path}/_exec_init.h"
            exec_path = f"{tmp_path}/run"
            with open(init_header_path, "w") as f:
                f.write(INIT_TEMPLATE)
            with open(source_path, "w") as f:
                f.write('#include "_exec_init.h"\n')
                f.write(script)
            result = execute(
                {'args': [self.compiler_path,  "-O2", source_path,  "-o", exec_path]}
            )
            if not result.success:
                raise CompileError(result.stderr)
            yield [exec_path]

    def execute_script(self, script, stdin=None):
        try:
            return super().execute_script(script, stdin)
        except CompileError as e:
            return ProcessExecuteResult(stdout='', stderr=str(e), exit_code=COMPILE_ERROR_EXIT_CODE, cost=0)
