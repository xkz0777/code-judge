from contextlib import asynccontextmanager
import logging

import fastapi
import uvicorn.logging

from app.model import (
    Submission,
    BatchSubmission,
    JudgeResult,
    BatchJudgeResult,
)
from app.judge import judge as _judge, judge_batch as _judge_batch
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


@app.get('/ping')
def ping():
    return 'pong'


@app.post('/run')
async def run(submission: Submission):
    return await _judge(redis_queue, submission)


@app.post('/run/batch')
async def run_batch(batch_sub: BatchSubmission):
    return await _judge_batch(redis_queue, batch_sub)


@app.post('/judge')
async def judge(submission: Submission):
    return JudgeResult.from_submission_result(await _judge(redis_queue, submission))


@app.post('/judge/batch')
async def judge_batch(batch_sub: BatchSubmission):
    return BatchJudgeResult.from_submission_result(await _judge_batch(redis_queue, batch_sub))
