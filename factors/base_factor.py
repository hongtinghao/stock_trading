"""
因子基类
所有因子都应该继承这个基类，确保一致的接口和功能
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

class BaseFactor(ABC):
    """因子抽象基类"""
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        # 计算因子值，data包含OHLCV及基本面数据，返回Series（index=date, columns=stock_code）=
        pass

    def preprocess(self, series: pd.Series) -> pd.Series:
        # 可选的预处理（在合成之前调用）
        return series