from functools import partial
import subprocess
from dataclasses import dataclass, field
import time
from contextlib import contextmanager
from typing import Any, Generator, Protocol


class ExecuteResult(Protocol):
    success: bool
    cost: float # in seconds


class Executor:
    def execute(self, config: dict[str, Any], stdin: str | None = None, timeout: float | None = None) -> ExecuteResult:
        ...


@dataclass
class ProcessExecuteResult:
    stdout: str
    stderr: str
    exit_code: int
    cost: float # in seconds
    success: bool = field(init=False)

    def __post_init__(self):
        self.success = self.exit_code == 0


class CompileError(Exception):
    pass


TIMEOUT_EXIT_CODE = -101
COMPILE_ERROR_EXIT_CODE = -102


def _init_limits(timeout: int | None = None, max_memory: int | None = None):
    import signal
    import os
    import resource

    def _exec_set_alarm_timeout(timeout):
        signal.signal(signal.SIGALRM, _exec_time_exceeded)
        signal.alarm(timeout)

    # checking time limit exceed
    def _exec_time_exceeded(*_):
        print('Suicide from timeout.', flush=True)
        os.kill(os.getpid(), signal.SIGKILL)

    def _exec_set_max_runtime(seconds):
        # setting up the resource limit
        soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
        resource.setrlimit(resource.RLIMIT_CPU, (seconds, hard))
        signal.signal(signal.SIGXCPU, _exec_time_exceeded)

    def _exec_limit_memory(maxsize):
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (maxsize, hard))

    if timeout:
        _exec_set_alarm_timeout(timeout)
        _exec_set_max_runtime(timeout)

    if max_memory:
        _exec_limit_memory(max_memory)


def execute(config: dict[str, Any], stdin: str | None = None, timeout: int | None = None, max_memory: int | None = None) -> ProcessExecuteResult:
    time_start = time.perf_counter()
    try:
        args = config['args']
        std_input = stdin.encode() if stdin else None
        result = subprocess.run(
            args,
            preexec_fn=partial(_init_limits, timeout, max_memory),
            shell=False,
            check=False,
            capture_output=True,
            timeout=timeout,
            input=std_input,
        )
        stdout = result.stdout.decode()
        stderr = result.stderr.decode()
        exit_code = result.returncode
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode()
        stderr = e.stderr.decode()
        exit_code = TIMEOUT_EXIT_CODE

    time_end = time.perf_counter()

    return ProcessExecuteResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        cost=time_end - time_start
    )


class ScriptExecutor:
    def __init__(self, timeout: int | None = None, max_memory: int | None = None):
        self.timeout = timeout
        self.max_memory = max_memory

    @contextmanager
    def setup_command(self, script: str) -> Generator[list[str], Any, None]:
        """
        Prepare the command to execute the script
        """
        raise NotImplementedError

    def process_result(self, result: ProcessExecuteResult) -> ProcessExecuteResult:
        return result

    def execute_script(self, script: str, stdin: str | None = None) -> ProcessExecuteResult:
        with self.setup_command(script) as command:
            return self.process_result(execute({'args': command}, stdin=stdin))
