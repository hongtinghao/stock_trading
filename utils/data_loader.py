"""
数据加载器模块
负责从不同数据源加载金融数据，支持缓存和本地存储
"""
import random

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import time
import requests
import json
import akshare as ak
import baostock as bs
from tqdm import tqdm  # 进度条

from config.settings import settings
from config.instruments import instrument_manager
from utils.logger import get_logger
from models.factory import ModelFactory

class DataLoader:
    """数据加载器类"""

    def __init__(self, source: str= None):
        """
        初始化数据加载器

        Args:
            source: 指定数据源，若不指定则从 settings.DATA_SOURCES['active'] 读取可选 "baostock", "akshare"
        """
        self.data_cache = {}  # 内存缓存
        self.logger = get_logger("data")
        self.source = source or settings.DATA_SOURCES.get('active', 'baostock')
        self.source = self.source.lower()
        self._init_data_source()
        self.logger.info(f"数据加载器初始化完成，数据源: {self.source}")

        self.source_config = settings.DATA_SOURCES.get(self.source, {})
        self.proxy = self.source_config.get('proxy', None)
        self.retry = self.source_config.get('retry', 3)
        self.timeout = self.source_config.get('timeout', 10)
        self.username = self.source_config.get('username', '')
        self.password = self.source_config.get('password', '')

    def _init_data_source(self):
        """初始化数据源"""
        if self.source == "baostock":
            try:
                time.sleep(random.uniform(1, 2))
                # 登录Baostock
                lg = bs.login()
                if lg.error_code != '0':
                    self.logger.error(f"Baostock登录失败: {lg.error_msg}")
                    self.source = "akshare"  # 回退到AKShare
                else:
                    self.logger.info("Baostock登录成功")
            except Exception as e:
                self.logger.error(f"Baostock初始化失败: {e}")
                self.source = "akshare"

    def load_data_with_sentiment(self, symbol: str, start_date: str, end_date: str, force_regenerate: bool = False) -> pd.DataFrame:
        """
        加载价格数据，并自动合并情感分数（如有新闻数据则实时生成）
        """
        # 先尝试读取已处理的情感数据文件
        processed_file = f"data/processed/{symbol}_with_sentiment.csv"
        if not force_regenerate and os.path.exists(processed_file):
            # 使用 index_col='date' 直接读取并设置日期索引
            df = pd.read_csv(processed_file, index_col='date', parse_dates=True)
            # 确保索引是 DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            # 检查日期范围是否覆盖
            if df.index.min() <= pd.to_datetime(start_date) and df.index.max() >= pd.to_datetime(end_date):
                self.logger.info(f"从缓存加载情感数据: {processed_file}")
                mask = (df.index >= start_date) & (df.index <= end_date)
                return df.loc[mask].copy()
            else:
                self.logger.info("缓存文件日期范围不足，重新生成")

        # 加载价格数据
        price_df = self.load_data(symbol, start_date, end_date, force_download=False)
        if price_df.empty:
            return price_df

        # 加载新闻数据
        news_path = f"data/raw/news/{symbol}_news.csv"
        news_df = pd.DataFrame()
        if os.path.exists(news_path):
            # 本地文件存在，直接读取
            news_df = pd.read_csv(news_path, parse_dates=['date'])
            self.logger.info(f"从本地读取新闻: {news_path}")
        else:
            # 本地文件不存在，根据配置决定是否下载
            if hasattr(settings, 'NEWS_SOURCE') and settings.NEWS_SOURCE['source'] == 'api':
                self.logger.info(f"本地新闻文件不存在，尝试从API下载...")
                download_success = self._download_news_to_local(symbol, start_date, end_date)
                if download_success and os.path.exists(news_path):
                    news_df = pd.read_csv(news_path, parse_dates=['date'])
            else:
                self.logger.warning(f"新闻文件不存在且未启用API下载: {news_path}")

        if news_df.empty:
            self.logger.warning("无新闻数据，情感分数设为0")
            price_df['sentiment'] = 0.0
            return price_df

        # 过滤新闻日期范围（略宽于价格范围，避免边界缺失）
        news_start = pd.to_datetime(start_date) - pd.Timedelta(days=1)
        news_end = pd.to_datetime(end_date) + pd.Timedelta(days=1)
        news_df = news_df[(news_df['date'] >= news_start) & (news_df['date'] <= news_end)]

        # 初始化模型
        model = ModelFactory.create_model(provider=settings.MODEL_CONFIG['provider'])

        # 按日期聚合新闻，生成情感分数
        sentiment_list = []
        # 按日期分组（去掉时间部分）
        news_df['date_only'] = news_df['date'].dt.date
        for date, group in news_df.groupby('date_only'):
            # 合并当日所有新闻标题（可考虑内容）
            headlines = group['headline'].tolist()
            # 如果有多条，可以平均或加权，这里简单平均
            scores = []
            for h in headlines:
                # 调用模型（假设模型predict接受{'headline': text}）
                score = model.predict({'headline': h})
                scores.append(score)
            avg_score = sum(scores) / len(scores) if scores else 0.0
            sentiment_list.append({'date': pd.to_datetime(date), 'sentiment': avg_score})

        sentiment_df = pd.DataFrame(sentiment_list)

        # 合并价格和情感
        merged = pd.merge(price_df, sentiment_df, on='date', how='left')
        merged['sentiment'] = merged['sentiment'].fillna(0.0)

        # 保存到processed目录
        merged.set_index('date', inplace=True)
        merged.to_csv(processed_file, index=True, index_label='date')
        self.logger.info(f"情感数据已生成并保存: {processed_file}")

        return merged

    def load_data( self, symbol: str, start_date: str, end_date: str, timeframe: str = "daily", adjust: str = "hfq",  # 复权类型: hfq(后复权), qfq(前复权), None(不复权)
            force_download: bool = False, save_local: bool = True ) -> pd.DataFrame:
        """
        加载数据

        Args:
            symbol: 标的代码，如 "000001.SZ"
            start_date: 开始日期，格式 "YYYY-MM-DD"
            end_date: 结束日期，格式 "YYYY-MM-DD"
            timeframe: 时间框架，"daily"（日线）, "weekly"（周线）, "monthly"（月线）
            adjust: 复权类型
            force_download: 是否强制重新下载
            save_local: 是否保存到本地

        Returns:
            pd.DataFrame: OHLCV数据
        """
        # 生成缓存键
        cache_key = f"{symbol}_{start_date}_{end_date}_{timeframe}_{adjust}"

        # 检查缓存
        if cache_key in self.data_cache and not force_download:
            self.logger.debug(f"从缓存加载数据: {cache_key}")
            return self.data_cache[cache_key].copy()

        # 检查本地文件
        local_file = self._get_local_file_path(symbol, timeframe, adjust)
        if local_file.exists() and not force_download:
            try:
                df = self._load_from_local(local_file, start_date, end_date)
                if not df.empty:
                    self.data_cache[cache_key] = df
                    return df.copy()
            except Exception as e:
                self.logger.warning(f"从本地加载失败: {e}")

        # 从数据源下载
        self.logger.info(f"下载数据: {symbol} ({start_date} 至 {end_date})")

        try:
            if self.source == "akshare":
                df = self._download_from_akshare(symbol, start_date, end_date, timeframe, adjust)
            elif self.source == "baostock":
                df = self._download_from_baostock(symbol, start_date, end_date, timeframe, adjust)
            else:
                raise ValueError(f"不支持的数据源: {self.source}")

            if df.empty:
                self.logger.warning(f"下载的数据为空: {symbol}")
                return df

            # 预处理数据
            df = self._preprocess_data(df, symbol)
            # 缓存数据
            self.data_cache[cache_key] = df
            # 保存到本地
            if save_local:
                self._save_to_local(df, local_file)

            self.logger.info(f"数据下载完成: {symbol}, 共 {len(df)} 条记录")
            return df.copy()

        except Exception as e:
            self.logger.error(f"数据下载失败 {symbol}: {e}")
            return pd.DataFrame()

    def _download_from_akshare(self, symbol: str, start_date: str, end_date: str, timeframe: str, adjust: str) -> pd.DataFrame:
        """从AKShare下载数据"""

        stock_code = symbol.split('.')[0]
        start_date_str = start_date.replace("-", "")
        end_date_str = end_date.replace("-", "")
        if timeframe == "daily":
            adjust_map = {
                "hfq": "qfq",  # AKShare中qfq是前复权，但实际是后复权效果
                "qfq": "hfq",
                None: "",
            }
            adjust_flag = adjust_map.get(adjust, "")

            for attempt in range(self.retry):
                try:
                    time.sleep(random.uniform(1, 2))
                    df = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="daily",
                        start_date=start_date_str,
                        end_date=end_date_str,
                        adjust=adjust_flag if adjust_flag else ""
                    )
                    if df.empty:
                        return df

                    # 重命名列
                    column_map = {
                        '日期': 'date',
                        '开盘': 'open',
                        '收盘': 'close',
                        '最高': 'high',
                        '最低': 'low',
                        '成交量': 'volume',
                        '成交额': 'amount',
                        '振幅': 'amplitude',
                        '涨跌幅': 'pct_change',
                        '涨跌额': 'change',
                        '换手率': 'turnover'
                    }
                    df = df.rename(columns=column_map)[list(column_map.values())]
                    # 设置日期索引
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    required_cols = ['open', 'high', 'low', 'close', 'volume']
                    df = df[required_cols]
                    return df

                except Exception as e:
                    self.logger.error(f"AKShare下载失败 (尝试 {attempt + 1}/{self.retry}): {e}")
                    if attempt < self.retry - 1:
                        wait_time = self.timeout  # 或者指数退避
                        self.logger.info(f"等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        self.logger.error(f"AKShare下载最终失败")
                        return pd.DataFrame()

        else:
            raise ValueError(f"不支持的时间框架: {timeframe}")

    def _download_from_baostock(self, symbol: str, start_date: str, end_date: str, timeframe: str,  adjust: str) -> pd.DataFrame:
        """从Baostock下载数据"""

        freq_map = {
            "daily": "d",
            "weekly": "w",
            "monthly": "m"
        }
        adjust_map = {
            "hfq": "3",  # 后复权
            "qfq": "2",  # 前复权
            None: "1",  # 不复权
        }
        frequency = freq_map.get(timeframe, "d")
        adjustflag = adjust_map.get(adjust, "3")
        symbol = symbol.split('.')[1]+"."+symbol.split('.')[0]
        time.sleep(random.uniform(1, 2))

        for attempt in range(self.retry):
            try:
                time.sleep(random.uniform(1, 2))
                rs = bs.query_history_k_data_plus(
                    symbol,
                    "date,open,high,low,close,volume,amount,turn",
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                    adjustflag=adjustflag
                )
                # 转换为DataFrame
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                if not data_list:
                    return pd.DataFrame()
                df = pd.DataFrame(data_list, columns=rs.fields)

                # 数据类型转换
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                for col in ['open', 'high', 'low', 'close']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                return df[['open', 'high', 'low', 'close', 'volume']]

            except Exception as e:
                self.logger.error(f"Baostock下载失败 (尝试 {attempt + 1}/{self.retry}): {e}")
                if attempt < self.retry - 1:
                    wait_time = self.timeout
                    self.logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Baostock下载最终失败")
                    return pd.DataFrame()

    def _get_news_from_akshare(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        使用 AkShare 获取个股新闻
        """
        self.logger.info(f"从 AkShare 获取新闻: {symbol}")
        try:
            code = symbol.split('.')[0]
            df = ak.stock_news_em(symbol=code)
            if df.empty:
                return df

            # 处理列名和日期
            df['date'] = pd.to_datetime(df['发布时间']).dt.date
            df['headline'] = df['新闻标题']
            df['link'] = df['新闻链接']
            #df['keywords'] = df['关键字']
            #df['source'] = df['文章来源']
            df['content'] = df['新闻内容']

            # 按日期范围过滤
            mask = (df['date'] >= pd.to_datetime(start_date).date()) & (df['date'] <= pd.to_datetime(end_date).date())
            df = df.loc[mask].copy()

            return df[['date', 'headline', 'content']]
        except Exception as e:
            self.logger.error(f"AkShare 获取新闻失败: {e}")
            return pd.DataFrame()

    def _download_news_to_local(self, symbol: str, start_date: str, end_date: str) -> bool:
        """
        下载指定股票在日期范围内的新闻，并保存到本地文件
        Returns:
            bool: 是否成功下载并保存（至少有一条新闻）
        """
        news_dir = Path(settings.NEWS_SOURCE['base_path'])
        news_dir.mkdir(parents=True, exist_ok=True)
        news_path = news_dir / f"{symbol}_news.csv"

        self.logger.info(f"开始下载新闻: {symbol} {start_date} -> {end_date}")
        try:
            # 调用已有的 AkShare 新闻获取方法
            df = self._get_news_from_akshare(symbol, start_date, end_date)
            if df.empty:
                self.logger.warning(f"未获取到新闻数据: {symbol}")
                # 保存一个空文件，避免反复尝试下载
                pd.DataFrame(columns=['date', 'headline', 'content']).to_csv(news_path, index=False)
                return False

            # 保存到本地
            df.to_csv(news_path, index=False)
            self.logger.info(f"新闻数据已保存至: {news_path}，共 {len(df)} 条")
            return True
        except Exception as e:
            self.logger.error(f"下载新闻失败: {e}")
            return False

    def _preprocess_data(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """数据预处理"""
        if df.empty:
            return df

        # 去除重复日期
        df = df[~df.index.duplicated(keep='first')]
        # 按日期排序
        df = df.sort_index()
        # 向前填充缺失值
        df = df.ffill()
        # 再丢弃仍未补上的缺失行
        df = df.dropna()
        # 验证数据有效性
        # 确保high >= low
        invalid_mask = (df['high'] < df['low']) | (df['close'] > df['high']) | (df['close'] < df['low'])
        if invalid_mask.any():
            self.logger.warning(f"{symbol} 存在无效数据，已删除 {invalid_mask.sum()} 行")
            df = df[~invalid_mask]

        # 收益率(P_t − P_{t-1}) / P_{t-1}
        df['returns'] = df['close'].pct_change()
        # 对数收益率ln(P_t / P_{t-1})
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        # 添加成交量信息（20日平均成交量）
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
        return df

    def _get_local_file_path(self, symbol: str, timeframe: str, adjust: str) -> Path:
        """获取本地文件路径"""
        filename = f"{symbol}_{timeframe}_{adjust or 'none'}.csv"
        return settings.DATA_PROCESSED_DIR / filename

    def _load_from_local(self, filepath: Path, start_date: str, end_date: str) -> pd.DataFrame:
        """从本地文件加载数据"""
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        # 过滤日期范围
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        mask = (df.index >= start_dt) & (df.index <= end_dt)
        df = df.loc[mask]
        return df

    def _save_to_local(self, df: pd.DataFrame, filepath: Path):
        """保存数据到本地"""
        try:
            # 如果文件已存在，合并数据
            if filepath.exists():
                existing_df = pd.read_csv(filepath, index_col=0, parse_dates=True)
                # 合并数据，新数据优先
                combined_df = pd.concat([existing_df, df])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                combined_df = combined_df.sort_index()
                df = combined_df
            # 保存到CSV
            df.to_csv(filepath)
            self.logger.debug(f"数据已保存到: {filepath}")
        except Exception as e:
            self.logger.error(f"保存数据失败: {e}")

    def load_multiple_data( self, symbols: List[str], start_date: str, end_date: str, **kwargs) -> Dict[str, pd.DataFrame]:
        """
        加载多个标的数据

        Args:
            symbols: 标的代码列表
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 传递给load_data的其他参数

        Returns:
            Dict[str, pd.DataFrame]: 数据字典
        """
        data_dict = {}
        self.logger.info(f"开始加载 {len(symbols)} 个标的数据")
        for symbol in tqdm(symbols, desc="加载数据"):
            df = self.load_data(symbol, start_date, end_date, **kwargs)
            if not df.empty:
                data_dict[symbol] = df
            else:
                self.logger.warning(f"数据加载失败: {symbol}")
        self.logger.info(f"数据加载完成，成功加载 {len(data_dict)}/{len(symbols)} 个标的")
        return data_dict

    def update_all_data(self, symbols: Optional[List[str]] = None, days_back: int = 365):
        """更新所有数据"""
        if symbols is None:
            symbols = instrument_manager.get_a_share_symbols()[:100]  # 限制前100个
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        self.logger.info(f"开始更新 {len(symbols)} 个标的数据")
        success_count = 0
        for symbol in tqdm(symbols, desc="更新数据"):
            try:
                df = self.load_data(symbol, start_date, end_date, force_download=True)
                if not df.empty:
                    success_count += 1
            except Exception as e:
                self.logger.error(f"更新失败 {symbol}: {e}")
        self.logger.info(f"数据更新完成，成功更新 {success_count}/{len(symbols)} 个标的")

    def get_data_info(self, symbol: str) -> Dict[str, Any]:
        """获取数据信息"""
        # 尝试加载最近一年的数据
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        df = self.load_data(symbol, start_date, end_date)
        if df.empty:
            return {"error": "数据为空"}
        info = {
            "symbol": symbol,
            "period": f"{df.index[0].date()} 至 {df.index[-1].date()}",
            "total_days": len(df),
            "start_price": df['close'].iloc[0],
            "end_price": df['close'].iloc[-1],
            "total_return": (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100,
            # 平均每日成交量
            "avg_volume": df['volume'].mean(),
            # 平均每日成交额
            "avg_turnover": df['volume'].mean() * df['close'].mean() if 'volume' in df.columns else 0,
            # 年化波动率
            "volatility": df['returns'].std() * np.sqrt(252) * 100,
            # 最大回撤
            "max_drawdown": self._calculate_max_drawdown(df['close']),
        }
        return info

    def _calculate_max_drawdown(self, prices: pd.Series) -> float:
        """计算最大回撤"""
        cumulative_returns = (prices / prices.iloc[0]) - 1
        running_max = cumulative_returns.expanding().max()
        drawdown = cumulative_returns - running_max
        return drawdown.min() * 100

    def clear_cache(self):
        """清空缓存"""
        self.data_cache.clear()
        self.logger.info("数据缓存已清空")


# 创建全局数据加载器实例
data_loader = DataLoader()
