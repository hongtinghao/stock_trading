"""
多种因子实现
"""

import pandas as pd
import numpy as np
from .base_factor import BaseFactor

class PEFactor(BaseFactor):
    """市盈率因子（取倒数，低PE得分高）"""
    def __init__(self):
        super().__init__("pe")

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        pe = data['pe']
        pe = pe.replace([np.inf, -np.inf], np.nan)
        return 1.0 / pe

class ROEFactor(BaseFactor):
    """净资产收益率因子（高ROE得分高）"""
    def __init__(self):
        super().__init__("roe")

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        return data['roe']

class MomentumFactor(BaseFactor):
    """动量因子（过去N个月收益率）"""
    def __init__(self, months=6):
        super().__init__(f"mom_{months}m")
        self.months = months

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        # data 中需包含字段 f'mom_{months}m'
        col = f'mom_{self.months}m'
        if col not in data.columns:
            raise ValueError(f"缺少动量列 {col}")
        return data[col]

class SizeFactor(BaseFactor):
    """市值因子（小市值偏好，取负对数）"""
    def __init__(self):
        super().__init__("size")

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        return -np.log(data['market_cap'] + 1e-8)