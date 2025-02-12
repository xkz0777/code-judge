from app.libs.redis_queue import RedisQueue
import app.config as app_config


def connect_queue(is_async: bool = False) -> RedisQueue:
    return RedisQueue(
        redis_uri=app_config.REDIS_URI,
        queue_name=app_config.WORK_QUEUE_NAME,
        is_async=is_async,
    )
