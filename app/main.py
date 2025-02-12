import logging

import fastapi

from app.model import Submission, SubmissionResult, WorkPayload
from app.worker_manager import WorkerManager
from app.work_queue import connect_queue
import app.config as app_config

logger = logging.getLogger(__name__)
app = fastapi.FastAPI()

redis_queue = connect_queue(True)
if app_config.RUN_WORKERS:
    print('Running workers...')
    worker_manager =  WorkerManager()
    worker_manager.run_background()


@app.get('/ping')
def ping():
    return 'pong'


@app.post('/judge')
async def judge(submission: Submission):
    payload = WorkPayload(submission=submission)
    payload_json = payload.model_dump_json()
    await redis_queue.push(app_config.WORK_QUEUE_NAME, payload_json)
    result_queue_name = f'{app_config.REDIS_RESULT_PREFIX}{payload.work_id}'
    result_json = await redis_queue.block_pop(result_queue_name, app_config.MAX_EXECUTION_TIME)
    await redis_queue.delete(result_queue_name)
    if result_json is None: # timeout
        return SubmissionResult(sub_id=submission.sub_id, success=False, cost=0)
    else:
        return SubmissionResult.model_validate_json(result_json[1])
