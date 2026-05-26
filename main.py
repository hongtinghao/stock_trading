"""
主回测程序
用于执行单策略回测
"""
import backtrader as bt
import argparse
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from config.strategy_config import STRATEGY_CONFIG
from data.data_loader import data_loader
from strategies.sma_cross import SMACrossStrategy
from strategies.multi_factor_strategy import MultiFactorStrategy
from analyzers.risk_metrics import RiskMetrics
from utils.plotter import plotter
from data.complete_data import CompletePandasData

def run_backtest(strategy_name):
    """运行回测"""
    # 获取策略配置

    if strategy_name not in STRATEGY_CONFIG:
        print(f"未知策略: {strategy_name}")
        print(f"可用策略: {list(STRATEGY_CONFIG.keys())}")
        return
    config = STRATEGY_CONFIG[strategy_name]
    strategy_class = config['class']
    params = config['params']
    symbols = config['symbols']
    start_date = config['start_date']
    end_date = config['end_date']



    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    # 设置初始资金
    cerebro.broker.setcash(settings.BACKTEST_CONFIG['INITIAL_CASH'])
    # 设置佣金
    cerebro.broker.setcommission(commission=settings.BACKTEST_CONFIG['COMMISSION'])
    data_dict = data_loader.load_multiple(symbols, start_date, end_date)
    if len(data_dict) == 0:
        print("无有效数据")
        return

    # 逐个添加数据
    for sym, df in data_dict.items():
        # 转换为Backtrader数据格式
        data = CompletePandasData(dataname=df)
        # name 用于后续识别
        cerebro.adddata(data, name=sym)

    # 添加策略
    cerebro.addstrategy(strategy_class, **params)

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
    sharpe_ratio = strategy.analyzers.sharpe.get_analysis().get('sharperatio', None)
    if sharpe_ratio is not None:
        print(f"夏普比率: {sharpe_ratio:.2f}")
    else:
        print("夏普比率: 数据不足无法计算")
    print(f"最大回撤: {strategy.analyzers.drawdown.get_analysis().max.drawdown:.2f}%")

    # 风险指标
    risk_metrics = strategy.analyzers.risk_metrics.get_analysis()
    if risk_metrics:
        print(f"年化收益率: {risk_metrics['年化收益率']:.2%}")
        print(f"年化波动率: {risk_metrics['年化波动率']:.2%}")
        print(f"胜率: {risk_metrics['胜率']:.2%}")
        print(f"总交易次数: {risk_metrics['总交易次数']}")

    # 绘制图表
    plotter.plot_backtrader_results(cerebro, strategy_class.__name__, symbols, save=True, show=False)
    print(f"图表已保存至: {settings.EQUITY_CURVES_DIR}")

    return strategy


def main():
    """主函数"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--strategy', type=str, default='MultiFactor', help='策略名称')
    args = parser.parse_args()
    run_backtest(args.strategy)


if __name__ == '__main__':
    main()