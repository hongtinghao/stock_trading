from cache.redis_client import RedisClient

class RateLimiter:
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client

    def check(self, key: str, limit: int, window_sec: int) -> bool:
        """返回 True 表示通过（未超限），False 表示被限流"""
        return not self.redis.is_rate_limited(key, limit, window_sec)