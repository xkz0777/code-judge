from contextlib import asynccontextmanager
import logging
from time import time
import asyncio

import fastapi
import uvicorn.logging

from app.model import Submission, SubmissionResult, WorkPayload, BatchSubmission, BatchSubmissionResult
from app.worker_manager import WorkerManager
from app.work_queue import connect_queue
import app.config as app_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _set_access_log(_: fastapi.FastAPI):
    logger = logging.getLogger('uvicorn.access')
    console_formatter = uvicorn.logging.AccessFormatter(
        '%(levelprefix)s %(asctime)s - %(client_addr)s - "%(request_line)s" %(status_code)s',
        datefmt="%Y-%m-%d %H:%M:%S",
        use_colors=True,
    )
    old = logger.handlers[0].formatter
    logger.handlers[0].setFormatter(console_formatter)
    yield
    logger.handlers[0].setFormatter(old)


app = fastapi.FastAPI(lifespan=_set_access_log)


redis_queue = connect_queue(True)
if app_config.RUN_WORKERS:
    print('Running workers...')
    worker_manager =  WorkerManager()
    worker_manager.run_background()


async def _judge(submission: Submission):
    start_time = time()
    try:
        payload = WorkPayload(submission=submission)
        payload_json = payload.model_dump_json()
        await redis_queue.push(app_config.WORK_QUEUE_NAME, payload_json)
        result_queue_name = f'{app_config.REDIS_RESULT_PREFIX}{payload.work_id}'
        result_json = await redis_queue.block_pop(result_queue_name, app_config.MAX_EXECUTION_TIME)
        await redis_queue.delete(result_queue_name)
        if result_json is None: # timeout
            return SubmissionResult(sub_id=submission.sub_id, success=False, cost=time() - start_time)
        else:
            return SubmissionResult.model_validate_json(result_json[1])
    except Exception as e:
        logger.exception(f'Failed to judge submission {submission.sub_id}')
        return SubmissionResult(sub_id=submission.sub_id, success=False, cost=time() - start_time)


@app.get('/ping')
def ping():
    return 'pong'


@app.post('/judge')
async def judge(submission: Submission):
    return await _judge(submission)


@app.post('/judge/batch')
async def judge(batch_sub: BatchSubmission):
    return BatchSubmissionResult(
        sub_id=batch_sub.sub_id,
        results=await asyncio.gather(*[_judge(sub) for sub in batch_sub.submissions])
    )
