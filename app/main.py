import fastapi

from app.payload import Submission, SubmissionResult
from app.work_manager import WorkManager
from app.work_queue import connect_redis_queue
import app.config as app_config

app = fastapi.FastAPI()

redis_queue = connect_redis_queue(True)
work_manager =  WorkManager()


@app.get('/ping')
def ping():
    return 'pong'


@app.post('/judge')
async def judge(submission: Submission):
    sub_json = submission.model_dump_json()
    await redis_queue.push(app_config.WORK_QUEUE_NAME, sub_json)
    result_queue_name = f'{app_config.REDIS_RESULT_PREFIX}{submission.sub_id}'
    result_json = await redis_queue.block_pop(result_queue_name, app_config.MAX_EXECUTION_TIME)
    await redis_queue.delete(result_queue_name)
    if result_json is None:
        return SubmissionResult(sub_id=submission.sub_id, success=False, cost=0)
    return SubmissionResult.model_validate_json(result_json)
