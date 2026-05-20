"""
Redis 封装
"""

import redis
import json
import pandas as pd
from datetime import datetime
from typing import Optional, Dict

class RedisClient:
    def __init__(self, host='localhost', port=6379, db=0, password=None, decode_responses=True):
        self.pool = redis.ConnectionPool(
            host=host, port=port, db=db, password=password,
            decode_responses=decode_responses
        )
        self.client = redis.Redis(connection_pool=self.pool)

    # 行情缓存
    def set_quote(self, key: str, quote: Dict, ttl=86400):
        self.client.setex(key, ttl, json.dumps(quote))

    def get_quote(self, key: str) -> Optional[Dict]:
        raw = self.client.get(key)
        return json.loads(raw) if raw else None

    # 策略状态
    def set_strategy_state(self, strategy_name: str, key: str, value):
        self.client.hset(f"strategy:{strategy_name}", key, str(value))

    def get_strategy_state(self, strategy_name: str, key: str) -> Optional[str]:
        return self.client.hget(f"strategy:{strategy_name}", key)

    def save_strategy_full_state(self, strategy_name: str, state_dict: Dict):
        self.client.hset(f"strategy:{strategy_name}", mapping=state_dict)

    def load_strategy_full_state(self, strategy_name: str) -> Dict:
        return self.client.hgetall(f"strategy:{strategy_name}")

    # 订单队列
    def push_order(self, order_dict: Dict):
        self.client.rpush("pending_orders", json.dumps(order_dict))

    def pop_order(self) -> Optional[Dict]:
        data = self.client.lpop("pending_orders")
        return json.loads(data) if data else None

    # 限流
    def is_rate_limited(self, key: str, limit: int, window_sec: int) -> bool:
        """滑动窗口限流，返回 True 表示被限流"""
        current = self.client.incr(key)
        if current == 1:
            self.client.expire(key, window_sec)
        return current > limit