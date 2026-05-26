"""
因子预处理
"""

import pandas as pd
import numpy as np
from scipy.stats import rankdata

import statsmodels.api as sm

class FactorProcessor:
    @staticmethod
    def winsorize(series: pd.Series, limits=(0.01, 0.99)) -> pd.Series:
        # 去极值：百分位截尾
        lower = series.quantile(limits[0])
        upper = series.quantile(limits[1])
        return series.clip(lower, upper)

    @staticmethod
    def standardize(series: pd.Series) -> pd.Series:
        # 标准化：减去均值除以标准差
        return (series - series.mean()) / series.std()

    # @staticmethod
    # def neutralize(series: pd.Series, industry_dummies: pd.DataFrame, market_cap: pd.Series) -> pd.Series:
    #     # 行业市值中性化（残差法），行业dummy需提前准备
    #     # 示例：使用线性回归去除行业和市值影响
    #     X = pd.concat([industry_dummies, np.log(market_cap)], axis=1)
    #     X = sm.add_constant(X)
    #     model = sm.OLS(series, X, missing='drop').fit()
    #     return model.resid  # 中性化后的残差作为因子值

