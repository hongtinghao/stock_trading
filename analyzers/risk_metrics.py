"""
风险指标分析器
计算夏普比率、最大回撤、胜率等风险指标
"""
import backtrader as bt
import numpy as np
import pandas as pd


class RiskMetrics(bt.Analyzer):
    """风险指标分析器"""

    def __init__(self):
        self.returns = []
        self.equity_curve = []
        self.trades = []

    def next(self):
        # 记录每日收益率和权益曲线
        current_value = self.strategy.broker.getvalue()
        if hasattr(self, 'last_value'):
            daily_return = (current_value - self.last_value) / self.last_value
            self.returns.append(daily_return)
        self.last_value = current_value
        self.equity_curve.append(current_value)

    def notify_trade(self, trade):
        # 记录交易信息
        if not trade.isclosed:
            return

        # trade.size 在平仓后可能为0，需要从history计算实际成交数量
        if hasattr(trade, 'history') and trade.history:
            # 从交易历史计算总成交量（绝对值之和）
            total_size = sum(abs(t.size) for t in trade.history)
        else:
            # 没有history时使用abs(trade.size)，如果为0则默认为1（避免除零）
            total_size = abs(trade.size) if trade.size != 0 else 1
        if total_size > 0 and trade.pnl != 0:
            # 通过盈亏反推退出价格
            price_diff = trade.pnl / total_size
            exit_price = trade.price + price_diff
        else:
            # 无法计算时使用当前收盘价
            exit_price = self.strategy.data.close[0]

        self.trades.append({
            'entry_price': trade.price,
            'exit_price': exit_price,
            'pnl': trade.pnl,
            'pnlcomm': trade.pnlcomm,
            'size': total_size,  # 使用计算后的安全数量
            'entry_bar': trade.baropen,
            'exit_bar': trade.barclose,
        })

    def get_analysis(self):
        # 计算风险指标
        if len(self.returns) == 0:
            return {}

        returns_series = pd.Series(self.returns)
        equity_series = pd.Series(self.equity_curve)

        # 年化收益率
        total_return = (equity_series.iloc[-1] - equity_series.iloc[0]) / equity_series.iloc[0]
        annual_return = (1 + total_return) ** (252 / len(returns_series)) - 1

        # 年化波动率
        annual_volatility = returns_series.std() * np.sqrt(252)

        # 夏普比率（假设无风险利率为0）
        sharpe_ratio = annual_return / annual_volatility if annual_volatility != 0 else 0

        # 最大回撤
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max
        max_drawdown = drawdown.min()

        # 胜率
        win_rate = 0.0
        avg_win = 0.0
        avg_loss = 0.0
        profit_factor = 0.0
        if self.trades:
            winning_trades = [t for t in self.trades if t['pnl'] > 0]
            losing_trades = [t for t in self.trades if t['pnl'] <= 0]
            win_rate = len(winning_trades) / len(self.trades)
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0.0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0.0
            if avg_loss != 0:
                profit_factor = abs(avg_win / avg_loss)
            else:
                profit_factor = float('inf') if avg_win > 0 else 0.0

        return {
            '总收益率': total_return,
            '年化收益率': annual_return,
            '年化波动率': annual_volatility,
            '夏普比率': sharpe_ratio,
            '最大回撤': max_drawdown,
            '总交易次数': len(self.trades),
            '胜率': win_rate,
            '平均收益': np.mean([t['pnl'] for t in self.trades]) if self.trades else 0,
            '平均亏损': avg_loss,
            '盈亏比': profit_factor,
        }