"""
主回测程序
用于执行单策略回测
"""
import backtrader as bt
from datetime import datetime
import argparse
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_trading.config.settings import settings
from stock_trading.utils.data_loader import data_loader
from stock_trading.strategies.sma_cross import SMACrossStrategy
from stock_trading.analyzers.risk_metrics import RiskMetrics
from stock_trading.utils.plotter import plotter


class PandasDataWithSentiment(bt.feeds.PandasData):
    """支持 sentiment 列的 PandasData"""
    lines = ('sentiment',)
    params = (('sentiment', -1),)


def run_backtest(strategy_class, symbol, start_date, end_date, **kwargs):
    """运行回测"""

    # 创建Cerebro引擎
    cerebro = bt.Cerebro()

    # 设置初始资金
    cerebro.broker.setcash(settings.BACKTEST_CONFIG['INITIAL_CASH'])

    # 设置佣金
    cerebro.broker.setcommission(
        commission=settings.BACKTEST_CONFIG['COMMISSION'],
    )

    # df = load_data(symbol, start_date, end_date)
    # 新闻情感
    df = data_loader.load_data_with_sentiment(symbol, start_date, end_date)
    if df.empty:
        print(f"无法加载数据: {symbol}")
        return

    # 转换为Backtrader数据格式
    # data = bt.feeds.PandasData(dataname=df)
    # 加入 sentiment 新闻情感
    data = PandasDataWithSentiment(dataname=df)
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(strategy_class, **kwargs)

    # 添加分析器
    # 夏普比率（Sharpe Ratio）衡量单位风险下的超额收益
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    # 最大回撤（Max DrawDown）及回撤持续期
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    # 总收益、年化收益、波动率
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    # 自定义风险指标
    cerebro.addanalyzer(RiskMetrics, _name='risk_metrics')

    # 运行回测
    print(f'初始资金: {cerebro.broker.getvalue():.2f}')
    results = cerebro.run()
    print(f'最终资金: {cerebro.broker.getvalue():.2f}')

    # 获取回测结果
    strategy = results[0]

    # 打印分析结果
    print("\n========== 回测结果 ==========")
    print(f"总收益率: {strategy.analyzers.returns.get_analysis()['rtot']:.2%}")
    print(f"夏普比率: {strategy.analyzers.sharpe.get_analysis()['sharperatio']:.2f}")
    print(f"最大回撤: {strategy.analyzers.drawdown.get_analysis().max.drawdown:.2%}")

    # 风险指标
    risk_metrics = strategy.analyzers.risk_metrics.get_analysis()
    if risk_metrics:
        print(f"年化收益率: {risk_metrics['年化收益率']:.2%}")
        print(f"年化波动率: {risk_metrics['年化波动率']:.2%}")
        print(f"胜率: {risk_metrics['胜率']:.2%}")
        print(f"总交易次数: {risk_metrics['总交易次数']}")

    # 绘制图表
    plotter.plot_backtrader_results(cerebro, strategy_class.__name__, symbol, save=True, show=False)
    print(f"图表已保存至: {settings.EQUITY_CURVES_DIR}")

    return strategy


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='运行策略回测')
    parser.add_argument('--strategy', type=str, default='SMACross', help='策略名称 (默认: SMACross)')
    parser.add_argument('--symbol', type=str, default='600110.SH', help='股票代码 (默认: 600110.SH)')
    parser.add_argument('--start', type=str, default='2025-02-14', help='开始日期 (默认: 2025-02-5)')
    parser.add_argument('--end', type=str, default='2026-3-13', help='结束日期 (默认: 2026-3-17)')
    parser.add_argument('--fast', type=int, default=10, help='快线周期 (默认: 10)')
    parser.add_argument('--slow', type=int, default=30, help='慢线周期 (默认: 30)')

    args = parser.parse_args()

    # 策略映射
    strategies = {
        'SMACross': SMACrossStrategy,
    }

    if args.strategy not in strategies:
        print(f"未知策略: {args.strategy}")
        print(f"可用策略: {list(strategies.keys())}")
        return

    strategy_class = strategies[args.strategy]

    # 运行回测
    run_backtest(
        strategy_class=strategy_class,
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        fast_period=args.fast,
        slow_period=args.slow
    )


if __name__ == '__main__':
    main()