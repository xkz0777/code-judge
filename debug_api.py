import os
os.environ['RUN_WORKERS'] = '1'
os.environ['MAX_WORKERS'] = '1'
if os.environ.get('REDIS_URI') is None:
    os.environ['REDIS_URI'] = 'redis://localhost:6379/10'

import logging
logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

import uvicorn

from app.main import app


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')
