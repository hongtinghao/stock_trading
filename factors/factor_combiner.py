"""
因子合成
"""

import pandas as pd
import numpy as np
from typing import Dict

class FactorCombiner:
    def __init__(self, weights: dict, method: str = 'rank'):
        """
        weights: {'pe': 0.2, 'roe': 0.3, 'mom_6m': 0.3, 'size': 0.2}
        method: 标准化方法，可选 'rank'（排名标准化）或 'zscore'（Z-score标准化）
        """
        self.weights = weights
        self.method = method

    def combine(self, factor_dict: Dict[str, pd.Series]) -> pd.Series:
        """输入多个因子的Series字典，输出综合得分Series"""
        total_score = None
        for name, series in factor_dict.items():
            w = self.weights.get(name, 0.0)
            if w == 0.0 or series.isnull().all():
                continue
            # 标准化
            if self.method == 'rank':
                # 排名百分比
                rank_pct = series.rank(pct=True)
                # 可选：进一步标准化为z-score（使均值为0，标准差为1）
                norm = (rank_pct - rank_pct.mean()) / rank_pct.std()
            elif self.method == 'zscore':
                norm = (series - series.mean()) / series.std()
            else:
                raise ValueError(f"不支持的方法: {self.method}")
            score = norm * w
            if total_score is None:
                total_score = score
            else:
                total_score = total_score.add(score, fill_value=0)
        return total_score