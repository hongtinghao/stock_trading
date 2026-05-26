import backtrader as bt
import pandas as pd
import numpy as np
from datetime import timedelta
from typing import Dict, List

from strategies.base_strategy import BaseStrategy
from data.data_loader import data_loader
from factors.factor_processor import FactorProcessor
from factors.factor_combiner import FactorCombiner
from factors.factor_library import PEFactor, ROEFactor, MomentumFactor, SizeFactor

class MultiFactorStrategy(BaseStrategy):
    """
    多因子选股策略
    - 定期调仓（每月/每周）
    - 综合因子得分选 top_n 股票等权配置
    - 支持个股止损
    """
    params = (
        ('rebalance_days', 21),          # 调仓间隔（交易日）
        ('top_n', 5),                   # 持仓股票数
        ('factor_weights', {             # 因子权重
            'pe': 0.2,
            'roe': 0.3,
            'momentum': 0.3,
            'size': 0.2
        }),
        ('stop_loss', -0.10),            # 个股止损线
        ('preprocess', True),            # 是否进行预处理（去极值、标准化）
        ('momentum_window', 120),        # 动量窗口
    )

    def __init__(self):
        super().__init__()
        # 股票池：从 cerebro 中获取所有数据源的 name
        self.stock_pool = [d._name for d in self.datas]
        self.last_rebalance_date = None
        # 记录每只股票的买入价格（用于止损）
        self.entry_prices = {}

        # 初始化因子实例
        self.factors = {
            'pe': PEFactor(),
            'roe': ROEFactor(),
            'momentum': MomentumFactor(months=6),
            'size': SizeFactor()
        }
        # 因子合成器
        self.combiner = FactorCombiner(self.params.factor_weights, method='rank')
        self.log(f"策略初始化，股票池大小: {len(self.stock_pool)}，持仓数量: {self.params.top_n}")

    def _init_indicators(self):
        pass  # 无需额外指标

    def next(self):
        current_date = self.datas[0].datetime.date(0)
        # 调仓判断
        if self.last_rebalance_date is None:
            self._rebalance(current_date)
            self.last_rebalance_date = current_date
        else:
            days_passed = (current_date - self.last_rebalance_date).days
            if days_passed >= self.params.rebalance_days:
                self._rebalance(current_date)
                self.last_rebalance_date = current_date

        # 每日止损检查
        self._check_stop_loss(current_date)

    def _rebalance(self, date):
        self.log(f"开始调仓，日期 {date}")
        # 获取所有股票的因子截面数据
        factor_dict = self._get_factor_cross_section(date)
        if not factor_dict:
            self.log("因子数据为空，跳过调仓")
            return

        # 合成综合得分
        total_score = self.combiner.combine(factor_dict)  # Series: stock -> score
        total_score = total_score.dropna()
        if total_score.empty:
            self.log("无有效得分，跳过")
            return

        # 选取得分最高的 top_n 只股票
        selected = total_score.sort_values(ascending=False).head(self.params.top_n).index.tolist()
        self.log(f"选中股票: {selected}")

        # 卖出不在新组合中的股票
        for stock in self.stock_pool:
            if stock not in selected and self.getposition(self._get_data(stock)).size != 0:
                self._close_position(stock)

        # 等权重买入新股票
        target_value_per_stock = self.broker.getvalue() / self.params.top_n
        for stock in selected:
            data = self._get_data(stock)
            if not data or len(data) == 0:
                continue
            current_price = data.close[0]
            if pd.isna(current_price) or current_price <= 0:
                continue
            target_size = int(target_value_per_stock / current_price)
            if target_size == 0:
                continue
            current_size = self.getposition(data).size
            if current_size != target_size:
                self.order_target_size(data=data, target=target_size)
                self.entry_prices[stock] = current_price
                self.log(f"调整 {stock}: 目标数量 {target_size}, 价格 {current_price:.2f}")

    def _get_factor_cross_section(self, date) -> Dict[str, pd.Series]:
        # 获取当前截面因子
        cross_data = {}
        date = pd.Timestamp(date)
        for data in self.datas:
            stock = data._name
            try:
                # 日期同步
                current_date = bt.num2date(data.datetime[0])
                if current_date.date() != pd.Timestamp(date).date():
                    continue
                # 当前价格
                close_price = data.close[0]
                # PE
                pe = data.pe_ttm[0] if hasattr(data, 'pe_ttm') else np.nan
                # ROE
                roe = data.roe[0] if hasattr(data, 'roe') else np.nan
                # 市值
                market_cap = data.total_capital[0] if hasattr(data, 'total_capital') else np.nan
                # 动量
                momentum = np.nan
                old_close = data.close[-self.params.momentum_window]
                if old_close > 0:
                    momentum = (close_price / old_close - 1)
                cross_data[stock] = {
                    'pe': pe,
                    'roe': roe,
                    'market_cap': market_cap,
                    'mom_6m': momentum
                }

            except Exception as e:
                self.log(f"{stock} 因子计算失败: {e}")
        if not cross_data:
            return {}
        # 转DataFrame
        df = pd.DataFrame(cross_data).T
        # 至少2个有效因子
        df = df.dropna(thresh=2)
        factor_values = {}
        for factor_name, factor_obj in self.factors.items():
            raw = factor_obj.calculate(df)
            if self.params.preprocess:
                raw = FactorProcessor.winsorize(raw)
                raw = FactorProcessor.standardize(raw)
            factor_values[factor_name] = raw
        return factor_values

    def _check_stop_loss(self, date):
        for stock in self.stock_pool:
            data = self._get_data(stock)
            if not data:
                continue
            pos = self.getposition(data)
            if pos.size == 0:
                continue
            entry_price = self.entry_prices.get(stock, pos.price)
            current_price = data.close[0]
            if pd.isna(current_price):
                continue
            pnl_pct = (current_price - entry_price) / entry_price
            if pnl_pct < self.params.stop_loss:
                self.log(f"止损 {stock}: 盈亏 {pnl_pct:.2%}")
                self._close_position(stock)

    def _close_position(self, stock):
        data = self._get_data(stock)
        if data:
            self.close(data=data)
            if stock in self.entry_prices:
                del self.entry_prices[stock]

    def _get_data(self, stock):
        for d in self.datas:
            if d._name == stock:
                return d
        return None