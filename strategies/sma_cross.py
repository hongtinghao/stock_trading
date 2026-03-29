"""
双均线交叉策略
当短期均线上穿长期均线时买入，下穿时卖出
"""
import backtrader as bt
from strategies.base_strategy import BaseStrategy


class SMACrossStrategy(BaseStrategy):
    """双均线交叉策略"""

    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('stop_loss', 0.05),
        ('take_profit', 0.10),
        ('sentiment_threshold', -0.1),
        ('name', 'SMA交叉策略'),
    )

    def _init_indicators(self):
        """初始化指标"""
        # 计算均线
        self.fast_sma = bt.indicators.SMA(
            self.data.close, period=self.params.fast_period)
        self.slow_sma = bt.indicators.SMA(
            self.data.close, period=self.params.slow_period)
        # 交叉信号
        self.crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma)

    def next(self):
        """主逻辑"""
        # 如果有未完成订单，不执行新逻辑
        if self.order:
            return

        # 新闻情感分数
        sentiment = self.data.sentiment[0]

        # 检查是否有持仓
        if not self.position:
            # 买入条件：金叉 + 新闻积极（大于阈值）
            if self.crossover > 0 and sentiment > self.params.sentiment_threshold:
                self.log(f'买入信号: 快线{self.fast_sma[0]:.2f} 上穿 慢线{self.slow_sma[0]:.2f}, 情感{sentiment:.2f}')
                size = self.broker.getcash() / self.data.close[0] * 0.9  # 使用90%资金
                size = int(size / 100) * 100  # 按手数取整
                if size > 0:
                    self.order = self.buy(size=size)
        else:
            # 卖出条件：死叉 或 情感极度消极（小于负阈值）
            if self.crossover < 0 or sentiment < -self.params.sentiment_threshold:
                self.log(f'卖出信号: 快线{self.fast_sma[0]:.2f} 下穿 慢线{self.slow_sma[0]:.2f}, 情感{sentiment:.2f}')
                self.order = self.sell(size=self.position.size)