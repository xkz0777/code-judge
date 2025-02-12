import os


env = os.environ.get


REDIS_URI = env('REDIS_URI')
if not REDIS_URI:
    raise ValueError('REDIS_URI is not set')

REDIS_RESULT_PREFIX = env('REDIS_RESULT_QUEUE_PREFIX', 'result-queue:')
REDIS_RESULT_EXPIRE = float(env('REDIS_RESULT_EXPIRE', 3600))  # default 1 hour

PYTHON_EXECUTOR_PATH = env('PYTHON_EXECUTOR_PATH', 'python3')

MAX_EXECUTION_TIME = float(env('MAX_EXECUTION_TIME', 10))  # default 10 seconds
MAX_WORKERS = int(env('MAX_WORKERS', os.cpu_count()))  # default 0, which means os.cpu_count()

WORK_QUEUE_NAME = env('WORK_QUEUE_NAME', 'work-queue')
