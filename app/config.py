import os


env = os.environ.get


REDIS_URI = env('REDIS_URI', '')
if not REDIS_URI:
    raise ValueError('REDIS_URI is not set')

REDIS_RESULT_PREFIX = env('REDIS_RESULT_QUEUE_PREFIX', 'result-queue:')
REDIS_RESULT_EXPIRE = int(env('REDIS_RESULT_EXPIRE', 3600))  # default 1 hour

MAX_EXECUTION_TIME = int(env('MAX_EXECUTION_TIME', 10))  # default 10 seconds
MAX_MEMORY = int(env('MAX_MEMORY', 256))  # default 256 MB
MAX_WORKERS = int(env('MAX_WORKERS', os.cpu_count())) or os.cpu_count()  # default os.cpu_count()

WORK_QUEUE_NAME = env('WORK_QUEUE_NAME', 'work-queue')

RUN_WORKERS = int(env('RUN_WORKERS', 0))  # default 0, which means run workers in a separate process


PYTHON_EXECUTOR_PATH = env('PYTHON_EXECUTOR_PATH', 'python3')
