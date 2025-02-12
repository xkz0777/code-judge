from multiprocessing import Process
import logging
import threading
from time import sleep

from app.payload import Submission, SubmissionResult
from app.libs.executors.python_executor import PythonExecutor, ScriptExecutor
import app.config as app_config
from app.work_queue import connect_redis_queue


logger = logging.getLogger(__name__)



def executor_factory(type: str) -> ScriptExecutor:
    if type == 'python':
        return PythonExecutor(python_path=app_config.PYTHON_EXECUTOR_PATH)
    else:
        raise ValueError(f'Unsupported type: {type}')


def judge(payload: Submission):
    try:
        executor = executor_factory(payload.type)
        result = executor.execute_script(payload.solution)
        sub_result = SubmissionResult(
            sub_id=payload.sub_id, success=result.success, cost=result.cost
        )
    except Exception as e:
        logger.exception(f'Worker failed to judge submission {payload.sub_id}')
        sub_result = SubmissionResult(
            sub_id=payload.sub_id, success=False, cost=0
        )
    return sub_result


class Worker(Process):
    def _run(self):
        redis_queue = connect_redis_queue(False)
        while True:
            sub_json = redis_queue.block_pop(app_config.WORK_QUEUE_NAME)[0]
            payload = Submission.model_validate_json(sub_json)
            result = judge(payload)
            result_queue_name = f'{app_config.REDIS_RESULT_PREFIX}{payload.sub_id}'
            redis_queue.expire(result_queue_name, app_config.REDIS_RESULT_EXPIRE)
            redis_queue.push(result_queue_name, result.model_dump_json())

    def run(self):
        while True:
            try:
                self._run()
            except Exception as e:
                logger.exception(f'Worker failed. Will retry in 60 seconds...')
                sleep(60)


class WorkManager:
    def __init__(self):
        max_workers = app_config.MAX_WORKERS
        self.workers: list[Worker] = []
        for _ in range(max_workers):
            worker = Worker()
            worker.start()
            self.workers.append(worker)

        self._check_lock = threading.Lock()
        self._check_thread = threading.Thread(target=self.check_workers, name='worker-check')
        self._check_thread.daemon = True
        self._check_thread.start()

    def check_workers(self):
        while True:
            try:
                self._check_workers()
            except Exception as e:
                logger.exception(f'Check worker failed. Will retry in 60 seconds...')
            sleep(60)

    def _check_workers(self):
        with self._check_lock:
            for i, worker in enumerate(self.workers):
                if not worker.is_alive():
                    logger.error('Worker dead. Restarting...')
                    worker = Worker()
                    worker.start()
                    self.workers[i] = worker

