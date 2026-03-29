"""
图表绘制模块
提供各种金融图表绘制功能，包括资金曲线、K线图、指标图等
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import gridspec
import matplotlib.ticker as ticker
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import seaborn as sns

from config.settings import settings
from utils.logger import get_logger


class Plotter:
    """图表绘制器"""

    def __init__(self, style: str = None):
        """
        初始化图表绘制器

        Args:
            style: 图表风格，默认使用settings中的配置
        """
        self.style = style or settings.PLOTTING_CONFIG['STYLE']
        self.figsize = settings.PLOTTING_CONFIG['FIG_SIZE']
        self.dpi = settings.PLOTTING_CONFIG['DPI']
        self.save_format = settings.PLOTTING_CONFIG['SAVE_FORMAT']
        self.logger = get_logger("plotter")

        # 设置样式
        plt.style.use(self.style)
        sns.set_palette("husl")

        self.logger.debug(f"图表绘制器初始化完成，样式: {self.style}")

    def plot_backtrader_results(self, cerebro, strategy_name: str, symbol: str, save: bool = True,
                                show: bool = False) -> Optional[plt.Figure]:
        """
        绘制Backtrader回测结果

        Args:
            cerebro: Backtrader引擎
            strategy_name: 策略名称
            symbol: 标的代码
            save: 是否保存图表
            show: 是否显示图表

        Returns:
            Optional[plt.Figure]: 图表对象
        """
        """
        图例区（左上角）                   
        - cash: 当前现金            
        - value: 总资产       
        交易盈亏标记（蓝色/红色圆点）
        - 蓝点(Positive): 盈利交易
        - 红点(Negative): 亏损交易
        主图：K线 + 双均线 + 买卖点
        - 绿色▲ = 买入信号（金叉）
        - 红色▼ = 卖出信号（死叉）
        - 红线(10日SMA): 7.42
        - 蓝线(30日SMA): 7.23
        - 成交量（红绿柱状）
        - 颜色与K线一致（红涨绿跌）
        副图：CrossOver指标
        - 1.0 = 金叉（快线上穿慢线）
        - -1.0 = 死叉（快线下穿慢线）
        - 0.0 = 无交叉  
        """
        try:
            # 使用非交互式后端，避免在服务器上显示图表
            import matplotlib
            matplotlib.use('Agg')

            # 绘制回测图表
            figs = cerebro.plot(style='candlestick', barup='green', bardown='red',
                                volume=True, figsize=self.figsize)

            if not figs:
                self.logger.warning("没有生成图表")
                return None

            fig = figs[0][0]
            # 添加标题
            strategy_title = f"{strategy_name} - {symbol}"
            fig.suptitle(strategy_title, fontsize=16, fontweight='bold')
            # 保存图表
            if save:
                timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{strategy_name}_{symbol}_{timestamp}.{self.save_format}"
                filepath = settings.EQUITY_CURVES_DIR / filename

                # 确保目录存在
                filepath.parent.mkdir(parents=True, exist_ok=True)

                fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                self.logger.info(f"图表已保存: {filepath}")

            # 显示图表
            if show:
                plt.show()
            else:
                plt.close(fig)

            return fig

        except Exception as e:
            self.logger.error(f"绘制Backtrader图表失败: {e}")
            return None


# 创建全局图表绘制器实例
plotter = Plotter()

