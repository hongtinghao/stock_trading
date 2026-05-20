"""
数据加载器模块
负责从不同数据源加载金融数据，支持缓存和本地存储
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from adapters.ifind_adapter import IFindAdapter, get_ifind_adapter
from config.settings import settings
from utils.logger import get_logger

class DataLoader:
    """数据加载器 - iFinD唯一数据源"""

    def __init__(self):
        self.data_cache = {}
        self.logger = get_logger("data")
        self.ifind = get_ifind_adapter()
        self.logger.info("数据加载器初始化完成，数据源: iFinD")

    def load_data(self, symbol: str, start_date: str, end_date: str, timeframe: str = "daily",
        adjust: str = "hfq",  # iFinD自动处理复权
        force_download: bool = False, save_local: bool = True) -> pd.DataFrame:
        cache_key = f"{symbol}_{start_date}_{end_date}_{timeframe}"

        # 检查缓存
        if cache_key in self.data_cache and not force_download:
            return self.data_cache[cache_key].copy()

        # 检查本地文件
        local_file = self._get_local_path(symbol, timeframe)
        if local_file.exists() and not force_download:
            df = self._load_local(local_file, start_date, end_date)
            if isinstance(df, pd.DataFrame) and not df.empty:
                self.data_cache[cache_key] = df
                return df.copy()

        # 从iFinD下载
        self.logger.info(f"从iFinD下载: {symbol}")
        period_map = {'daily': 'D', 'weekly': 'W', 'monthly': 'M'}
        period = period_map.get(timeframe, 'D')
        df = self.ifind.get_history_data(symbol, start_date, end_date, period)
        if df.empty:
            self.logger.warning(f"下载为空: {symbol}")
            return df

        # 预处理
        df = self._preprocess(df, symbol)
        self.data_cache[cache_key] = df
        if save_local:
            self._save_local(df, local_file)
        return df.copy()

    def _preprocess(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        # 数据预处理
        if df.empty:
            return df
        # 清洗
        df = df[~df.index.duplicated(keep='first')]
        df = df.sort_index()
        df = df.ffill().dropna()

        # 计算指标
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
        return df

    def _get_local_path(self, symbol: str, timeframe: str) -> Path:
        # 本地文件路径
        path = Path(f'data/raw')
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{symbol}_{timeframe}.csv"

    def _load_local(self, filepath: Path, start_date, end_date) -> pd.DataFrame:
        # 加载本地数据
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        data_start = df.index.min()
        data_end = df.index.max()
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        if data_start <= start_dt and end_dt <= data_end:
            mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
            return df.loc[mask]
        return False

    def _save_local(self, df: pd.DataFrame, filepath: Path):
        # 保存到本地
        if filepath.exists():
            existing = pd.read_csv(filepath, index_col=0, parse_dates=True)
            df = pd.concat([existing, df])
            df = df[~df.index.duplicated(keep='last')].sort_index()
        df.to_csv(filepath)

    def load_multiple(self, symbols: List[str], start_date: str, end_date: str, **kwargs) -> Dict[str, pd.DataFrame]:
        # 加载多个标的
        result = {}
        for symbol in symbols:
            df = self.load_data(symbol, start_date, end_date, **kwargs)
            if not df.empty:
                result[symbol] = df
        return result

    def get_realtime(self, symbol: str) -> Optional[Dict]:
        # 获取实时行情
        return self.ifind.get_realtime_quote(symbol)

    def clear_cache(self):
        # 清空缓存
        self.data_cache.clear()

    def test(self, symbol: str, start_date: str, end_date: str):
        # df1 = self.ifind.get_search_info("市盈率小于20的股票")
        # self._save_local(df1, Path("data/raw/智能收索.csv"))
        # params = ['ths_b3612_stock','2026-04-14,1,100,100']
        # params = ['ths_info_banktype_stock']
        # params = ['ths_holder_name_stock','2026-04-15,1']
        # df2 = self.ifind.get_basic_data(symbol, params)
        # self._save_local(df2, Path(f"data/raw/基本面数据.csv"))
        df3 = self.ifind.get_realtime_quote(symbol)
        self._save_local(df3, Path("data/raw/公告信息.csv"))
        df4 = self.ifind.get_holder_info(symbol)
        self._save_local(df4, Path("data/raw/获取股东信息.csv"))


# 全局实例
data_loader = DataLoader()
