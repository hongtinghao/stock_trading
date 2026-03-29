"""
KDJ指标实现
"""
import backtrader as bt


class KDJ(bt.Indicator):
    """
    KDJ指标
    公式:
        RSV = (收盘价 - N日内最低价) / (N日内最高价 - N日内最低价) * 100
        K = SMA(RSV, M1)
        D = SMA(K, M2)
        J = 3K - 2D
    """
    lines = ('k', 'd', 'j')
    params = (
        ('period', 9),
        ('period_k', 3),
        ('period_d', 3),
    )

    def __init__(self):
        # 计算N日内最高价和最低价
        self.high_n = bt.indicators.Highest(self.data.high, period=self.params.period)
        self.low_n = bt.indicators.Lowest(self.data.low, period=self.params.period)

        # 计算RSV
        rsv = (self.data.close - self.low_n) / (self.high_n - self.low_n) * 100

        # 计算K, D, J
        self.lines.k = bt.indicators.SMA(rsv, period=self.params.period_k)
        self.lines.d = bt.indicators.SMA(self.lines.k, period=self.params.period_d)
        self.lines.j = 3 * self.lines.k - 2 * self.lines.d