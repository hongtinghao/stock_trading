"""
实盘联调测试策略
每隔N根K线强制买卖一次,用于验证交易链路是否通畅
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy

class TestCycleStrategy(BaseStrategy):
    """实盘测试"""

    params = (
        ('cycle', 5),   # 每10根bar触发一次交易
        ('size', 100),  # 固定手数
        ('name', '测试循环策略'),
    )

    def __init__(self):
        super().__init__()
        self.counter = 0
        self.last_action = None  # buy / sell

    def next(self):
        self.counter += 1

        # 等数据稳定一点再开始
        if self.counter < self.params.cycle:
            return

        # 每 cycle 根bar触发一次
        if self.counter % self.params.cycle != 0:
            return

        # 如果有未完成订单，跳过
        if self.order:
            return

        if not self.position:
            self.log(f"[TEST] BUY trigger at bar={self.counter}")
            self.order = self.buy(size=self.params.size)
            self.last_action = "buy"
        else:
            self.log(f"[TEST] SELL trigger at bar={self.counter}")
            # self.order = self.sell(size=self.position.size)
            self.order = self.sell(size=self.params.size)
            self.last_action = "sell"