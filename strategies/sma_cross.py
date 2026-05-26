"""
双均线交叉策略
当短期均线上穿长期均线时买入，下穿时卖出
"""

import backtrader as bt
from strategies.base_strategy import BaseStrategy

class SMACrossStrategy(BaseStrategy):
    """双均线交叉策略"""

    params = (
        ('fast_period', 2),
        ('slow_period', 5),
        ('stop_loss', 0.05),
        ('take_profit', 0.10),
        ('name', 'SMA交叉策略'),
    )

    def _init_indicators(self):
        # 初始化指标，每个股票独立指标
        self.inds = {}
        for data in self.datas:
        # 计算均线
            fast_sma = bt.indicators.SMA(data.close, period=self.params.fast_period)
            slow_sma = bt.indicators.SMA(data.close, period=self.params.slow_period)
            # 交叉信号
            crossover = bt.indicators.CrossOver(fast_sma, slow_sma)
            self.inds[data] = {
                'fast_sma': fast_sma,
                'slow_sma': slow_sma,
                'crossover': crossover,
            }

    def next(self):
        # 确保已有足够的历史数据来计算慢速均线
        for data in self.datas:
            symbol = data._name
            if len(self.data) < self.params.slow_period:
                continue
            # 如果有未完成订单，不执行新逻辑
            if symbol in self.orders:
                continue

            inds = self.inds[data]
            fast_sma = inds['fast_sma']
            slow_sma = inds['slow_sma']
            crossover = inds['crossover']

            # 当前持仓
            position = self.getposition(data)

            # 没持仓
            if not position:
                # 金叉买入
                if crossover[0] > 0:
                    self.log(f'{symbol} 买入信号: 快线{fast_sma[0]:.2f} 上穿 慢线{slow_sma[0]:.2f}')
                    # 每只股票只用20%资金
                    cash = self.broker.getcash()
                    size = (cash * 0.2 / data.close[0])
                    size = int(size / 100) * 100
                    if size > 0:
                        order = self.buy(data=data, size=size)
                        self.orders[symbol] = order
            # 已持仓
            else:
                # 死叉卖出
                if crossover[0] < 0:
                    self.log(f'{symbol} 卖出信号: 快线{fast_sma[0]:.2f} 下穿 慢线{slow_sma[0]:.2f}')
                    order = self.sell(data=data, size=position.size)
                    self.orders[symbol] = order