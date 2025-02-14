from multiprocessing import Process
import logging
import threading
from time import sleep

from app.model import Submission, SubmissionResult, WorkPayload
from app.libs.executors.python_executor import PythonExecutor, ScriptExecutor
from app.libs.executors.cpp_executor import CppExecutor
import app.config as app_config
from app.work_queue import connect_queue


logger = logging.getLogger(__name__)



def executor_factory(type: str) -> ScriptExecutor:
    if type == 'python':
        return PythonExecutor(
            python_path=app_config.PYTHON_EXECUTOR_PATH,
            timeout=app_config.MAX_EXECUTION_TIME,
            memory_limit=app_config.MAX_MEMORY * 1024 * 1024,
        )
    elif type == 'cpp':
        return CppExecutor(
            compiler_path=app_config.CPP_COMPILER_PATH,
            timeout=app_config.MAX_EXECUTION_TIME,
            memory_limit=app_config.MAX_MEMORY * 1024 * 1024,
        )
    else:
        raise ValueError(f'Unsupported type: {type}')


def judge(sub: Submission):
    try:
        executor = executor_factory(sub.type)
        result = executor.execute_script(sub.solution, sub.input)
        # TODO: make this more robust
        success = result.success and result.stdout.strip() == sub.expected_output.strip()
        sub_result = SubmissionResult(
            sub_id=sub.sub_id, success=success, cost=result.cost
        )
    except Exception as e:
        logger.exception(f'Worker failed to judge submission {sub.sub_id}')
        sub_result = SubmissionResult(
            sub_id=sub.sub_id, success=False, cost=0
        )
    return sub_result


class Worker(Process):
    def _run_loop(self):
        redis_queue = connect_queue(False)
        while True:
            _, payload_json = redis_queue.block_pop(app_config.WORK_QUEUE_NAME)
            payload = WorkPayload.model_validate_json(payload_json)
            result = judge(payload.submission)
            result_queue_name = f'{app_config.REDIS_RESULT_PREFIX}{payload.work_id}'
            redis_queue.push(result_queue_name, result.model_dump_json())
            redis_queue.expire(result_queue_name, app_config.REDIS_RESULT_EXPIRE)

    def run(self):
        while True:
            try:
                self._run_loop()
            except Exception:
                logger.exception(f'Worker failed. Will retry in 60 seconds...')
                sleep(60)


class WorkerManager:
    def __init__(self):
        max_workers = app_config.MAX_WORKERS
        self.workers: list[Worker] = []
        logger.info(f'Starting {max_workers} workers...')
        for _ in range(max_workers):
            worker = Worker()
            worker.start()
            self.workers.append(worker)
        logger.info(f'Started {max_workers} workers')

    def run(self):
        while True:
            try:
                self._check_workers()
            except Exception as e:
                logger.exception(f'Check worker failed. Will retry in 60 seconds...')
            sleep(60)

    def run_background(self):
        self._check_thread = threading.Thread(target=self.run, name='worker-checker')
        self._check_thread.daemon = True
        self._check_thread.start()

    def _check_workers(self):
        for i, worker in enumerate(self.workers):
            if not worker.is_alive():
                logger.error('Worker dead. Restarting...')
                worker = Worker()
                worker.start()
                self.workers[i] = worker
