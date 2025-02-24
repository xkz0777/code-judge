from contextlib import contextmanager
import tempfile
import io

from .executor import ScriptExecutor, ProcessExecuteResult, TIMEOUT_EXIT_CODE


SCRIPT_ENDING_MARK = "@@E"
DURATION_MARK = "@@D"


PRE_TEMPLATE = f"""
import signal
import resource
import os
import time

# checking time limit exceed
def _exec_time_exceeded(signo, frame):
    raise SystemExit({TIMEOUT_EXIT_CODE})


def _exec_set_max_runtime(seconds):
    # setting up the resource limit
    soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
    resource.setrlimit(resource.RLIMIT_CPU, (seconds, hard))
    signal.signal(signal.SIGXCPU, _exec_time_exceeded)


def _exec_limit_memory(maxsize):
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (maxsize, hard))

resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
if {{timeout}}:
    _exec_set_max_runtime({{timeout}})

if {{memory_limit}}:
    _exec_limit_memory({{memory_limit}})

_exec_time_start = time.perf_counter()

""".strip()

POST_TEMPLATE = f"""

_exec_time_end = time.perf_counter()
_exec_duration = _exec_time_end - _exec_time_start
print("{SCRIPT_ENDING_MARK}")
print(f"{DURATION_MARK}{{_exec_duration}}", flush=True)

""".strip()

class PythonExecutor(ScriptExecutor):
    def __init__(self, python_path: str, timeout: int = None, memory_limit: int = None):
        self.timeout = timeout
        self.memory_limit = (
            memory_limit + 1024 * 1024 * 1024  # extra 1GB for python overhead
            if memory_limit
            else None
        )
        self.python_path = python_path

    @contextmanager
    def setup_command(self, script: str):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as f:
            f.write(PRE_TEMPLATE.format(timeout=self.timeout, memory_limit=self.memory_limit))
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
