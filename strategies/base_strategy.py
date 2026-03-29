"""
策略基类
所有策略都应该继承这个基类，确保一致的接口和功能
"""
import backtrader as bt
from utils.logger import get_logger


class BaseStrategy(bt.Strategy):
    """策略基类"""

    params = (
        ('name', 'BaseStrategy'),
        ('log', True),
        ('printout', False),
    )

    def __init__(self):
        """初始化策略"""
        self.logger = get_logger(self.params.name)
        self.order = None
        self.trade_count = 0
        self.bar_executed = None

        # 指标计算
        self._init_indicators()

    def _init_indicators(self):
        """初始化指标，由子类实现"""
        pass

    def next(self):
        """主逻辑，由子类实现"""
        pass

    def notify_order(self, order):
        """订单状态变化回调"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，无需操作
            return

        if order.status in [order.Completed]:
            # 订单已完成
            if order.isbuy():
                self.logger.info(f'买入执行, 价格: {order.executed.price:.2f}, '
                                 f'数量: {order.executed.size}, 成本: {order.executed.value:.2f}, '
                                 f'佣金: {order.executed.comm:.2f}')
            elif order.issell():
                self.logger.info(f'卖出执行, 价格: {order.executed.price:.2f}, '
                                 f'数量: {order.executed.size}, 收入: {order.executed.value:.2f}, '
                                 f'佣金: {order.executed.comm:.2f}')
            self.bar_executed = len(self)
            self.trade_count += 1

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.logger.warning(f'订单取消/保证金不足/拒绝 {order.getstatusname()}')

        # 重置订单
        self.order = None


    def notify_trade(self, trade):
        """交易结果回调"""
        if not trade.isclosed:
            return

        self.logger.info(f'交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')

    def log(self, txt, dt=None):
        """日志记录"""
        if self.params.log:
            dt = dt or self.datas[0].datetime.date(0)
            self.logger.info(f'{dt.isoformat()} {txt}')

    def print(self, txt, dt=None):
        """打印到控制台"""
        if self.params.printout:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')