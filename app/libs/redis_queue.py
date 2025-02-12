import redis
import socket

class RedisQueue:
    def __init__(self, redis_uri, queue_name, is_async: bool = False):
        self.redis_uri = redis_uri
        self.is_async = is_async
        self.queue_name = queue_name
        self.redis: redis.Redis | redis.asyncio.Redis = self._init_redis()

    def _init_redis(self) -> redis.Redis | redis.asyncio.Redis:
        Redis = redis.Redis if not self.is_async else redis.asyncio.Redis
        return Redis.from_url(
            self.redis_uri,
            socket_connect_timeout=120,
            socket_keepalive=True,
            socket_keepalive_options={socket.TCP_KEEPIDLE: 2, socket.TCP_KEEPINTVL: 1, socket.TCP_KEEPCNT: 2}
        )

    def push(self, queue_name, value):
        return self.redis.rpush(queue_name, value)

    def pop(self, queue_name):
        return self.redis.lpop(queue_name)

    def block_pop(self, queue_name, timeout=0):
        return self.redis.blpop(queue_name, timeout)

    def expire(self, key, timeout):
        return self.redis.expire(key, timeout)

    def delete(self, key):
        return self.redis.delete(key)