from contextlib import contextmanager
import tempfile
import io

from .executor import ScriptExecutor, ProcessExecuteResult, TIMEOUT_EXIT_CODE


SCRIPT_ENDING_MARK = "@@E"
DURATION_MARK = "@@D"


PRE_TEMPLATE = f"""
import time

_exec_time_start = time.perf_counter()

"""

POST_TEMPLATE = f"""

_exec_time_end = time.perf_counter()
_exec_duration = _exec_time_end - _exec_time_start
print("{SCRIPT_ENDING_MARK}")
print(f"{DURATION_MARK}{{_exec_duration}}", flush=True)

"""

class PythonExecutor(ScriptExecutor):
    def __init__(self, python_path: str, timeout: int = None, max_memory: int = None):
        super().__init__(timeout,
            max_memory + 1024 * 1024 * 1024  # extra 1GB for python overhead
            if max_memory
            else None
        )
        self.python_path = python_path

    @contextmanager
    def setup_command(self, script: str):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as f:
            f.write(PRE_TEMPLATE)
            f.write("\n")
            f.write(script)
            f.write("\n")
            f.write(POST_TEMPLATE)
            f.flush()
            yield [self.python_path, f.name]

    def process_result(self, result):
        if SCRIPT_ENDING_MARK in result.stdout:
            result.stdout, meta_info = result.stdout.split(SCRIPT_ENDING_MARK, 2)
            for line in io.StringIO(meta_info):
                if line.startswith(DURATION_MARK):
                    result.cost = float(line[len(DURATION_MARK):])
                    break
        return result
