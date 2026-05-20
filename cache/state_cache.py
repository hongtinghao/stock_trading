"""
策略状态持久化
"""

from cache.redis_client import RedisClient
from typing import Dict

class StrategyStateCache:
    def __init__(self, redis_client: RedisClient, strategy_name: str):
        self.redis = redis_client
        self.name = strategy_name

    def save(self, state: Dict):
        self.redis.save_strategy_full_state(self.name, state)

    def load(self) -> Dict:
        return self.redis.load_strategy_full_state(self.name)

    def get(self, key: str):
        return self.redis.get_strategy_state(self.name, key)

    def set(self, key: str, value):
        self.redis.set_strategy_state(self.name, key, value)