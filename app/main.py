from contextlib import asynccontextmanager
import logging
from time import time
import asyncio

import fastapi
import uvicorn.logging

from app.model import Submission, SubmissionResult, WorkPayload, \
    BatchSubmission, BatchSubmissionResult, ResultReason
from app.libs.utils import chunkify
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


def to_result(submission, start_time, result_json):
    if result_json is None: # timeout
        return SubmissionResult(sub_id=submission.sub_id, success=False, cost=time() - start_time, reason=ResultReason.QUEUE_TIMEOUT)
    else:
        result = SubmissionResult.model_validate_json(result_json[1])
        if not result.success and result.cost >= app_config.MAX_EXECUTION_TIME:
            result.reason = ResultReason.WORKER_TIMEOUT
        return result


async def _judge_batch(subs: list[Submission]):
    start_time = time()
    chunks = list(chunkify(subs, app_config.MAX_BATCH_CHUNK_SIZE))
    payload_chunks = [
        [WorkPayload(submission=sub) for sub in chunk]
        for chunk in chunks
    ]

    async def _submit(payload: WorkPayload):
        payload_json = payload.model_dump_json()
        await redis_queue.push(app_config.REDIS_WORK_QUEUE_NAME, payload_json)

    async def _get_result(payload: WorkPayload, max_wait_time):
        """max_wait_time <= 0 means no wait (which is different from block_pop)"""
        result_queue_name = f'{app_config.REDIS_RESULT_PREFIX}{payload.work_id}'
        if max_wait_time > 0:
            result_json = await redis_queue.block_pop(result_queue_name, max_wait_time)
        else:
            # no wait
            result_json = await redis_queue.pop(result_queue_name)
        await redis_queue.delete(result_queue_name)
        return to_result(payload.submission, start_time, result_json)

    # submit all submissions to the queue
    for chunk in payload_chunks:
        await asyncio.gather(*[_submit(pl) for pl in chunk])

    results = []
    max_wait_time = app_config.MAX_QUEUE_WAIT_TIME
    wait_start_time = time()
    for chunk in payload_chunks:
        # get all results from the queue
        left_time = int(max_wait_time - (time() - wait_start_time))
        chunk_results = await asyncio.gather(*[_get_result(pl, left_time) for pl in chunk])
        results.extend(chunk_results)
    return results


async def _judge(submission: Submission):
    start_time = time()
    try:
        payload = WorkPayload(submission=submission)
        payload_json = payload.model_dump_json()
        await redis_queue.push(app_config.REDIS_WORK_QUEUE_NAME, payload_json)
        result_queue_name = f'{app_config.REDIS_RESULT_PREFIX}{payload.work_id}'
        result_json = await redis_queue.block_pop(result_queue_name, app_config.MAX_QUEUE_WAIT_TIME)
        await redis_queue.delete(result_queue_name)
        return to_result(submission, start_time, result_json)
    except Exception:
        logger.exception(f'Failed to judge submission {submission.sub_id}')
        return SubmissionResult(sub_id=submission.sub_id, success=False, cost=time() - start_time, reason=ResultReason.INTERNAL_ERROR)


@app.get('/ping')
def ping():
    return 'pong'


@app.post('/judge')
async def judge(submission: Submission):
    return await _judge(submission)


@app.post('/judge/batch')
async def judge(batch_sub: BatchSubmission):
    if not app_config.MAX_BATCH_CHUNK_SIZE:
        return BatchSubmissionResult(
            sub_id=batch_sub.sub_id,
            results=await asyncio.gather(*[_judge(sub) for sub in batch_sub.submissions])
        )
    else:
        try:
            results = await _judge_batch(batch_sub.submissions)
        except Exception:
            logger.exception(f'Failed to judge batch submission {batch_sub.sub_id}')
            results=[
                SubmissionResult(
                    sub_id=sub.sub_id,
                    success=False,
                    cost=0,
                    reason=ResultReason.INTERNAL_ERROR
                ) for sub in batch_sub.submissions
            ]
        return BatchSubmissionResult(
            sub_id=batch_sub.sub_id,
            results=results
        )
