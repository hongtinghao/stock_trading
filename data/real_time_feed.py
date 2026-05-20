"""
    实盘实时数据源
"""

import json
from typing import Optional, List, Tuple
import backtrader as bt
import pandas as pd
import time
from datetime import datetime
from typing import Optional
from adapters.ifind_adapter import IFindAdapter
from utils.logger import get_logger


class THSRealtimeData(bt.DataBase):
    """基于 iFinD 实时行情的 DataFeed，合成分钟K线"""

    params = (
        ('symbol', ''),
        ('timeframe', bt.TimeFrame.Minutes),
        ('compression', 1),
        ('poll_interval', 1),
        ('live', True),
    )

    def __init__(self, ifind_adapter: IFindAdapter, redis_client=True):
        super().__init__()
        self.logger = get_logger('THSRealtimeData')
        self.adapter = ifind_adapter
        self.redis = redis_client
        self._bars = []  # 存储已合成的K线：[ (datetime, open, high, low, close, volume, openinterest) ]
        self._current_bar = None  # 当前正在合成的K线：dict
        self._last_bar_time = None  # 上根K线结束时间
        self._live = False
        self._last_total_volume = None
        self.redis_key = []


    def islive(self):
        return True

    def haslivedata(self):
        return True

    def _get_current_quote(self):
        df = self.adapter.get_realtime_quote(self.p.symbol)
        if df is None or df.empty:
            return None, None
        record = df.iloc[-1].to_dict()
        dt = pd.to_datetime(df.index[-1]).to_pydatetime()
        # 写入Redis
        if self.redis:
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
            key = f"quote:{self.params.symbol}:{date_str}:{time_str}"
            self.redis.set_quote(key, record, ttl=86400)
            self.redis_key.append(key)
        return record, dt

    def _push_bar(self, bar):
        self.lines.datetime[0] = bt.date2num(bar[0])
        self.lines.open[0] = bar[1]
        self.lines.high[0] = bar[2]
        self.lines.low[0] = bar[3]
        self.lines.close[0] = bar[4]
        self.lines.volume[0] = bar[5]
        self.lines.openinterest[0] = bar[6]

    def _load(self):
        # 先输出已完成bar
        if self._bars:
            bar = self._bars.pop(0)
            self._push_bar(bar)
            return True
        quote, quote_time = self._get_current_quote()
        if quote is None:
            return None
        if not self._live:
            self.put_notification(self.LIVE)
            self._live = True

        price = float(quote.get('latest', 0))
        total_volume = float(quote.get('volume', 0))
        bar_time = quote_time.replace(second=0, microsecond=0)

        # 第一笔
        if self._current_bar is None:
            self._current_bar = {
                'time': bar_time,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': 0
            }
            self._last_bar_time = bar_time
            self._last_total_volume = total_volume
            return None

        # 计算分钟成交量
        minute_volume = max(total_volume - self._last_total_volume, 0)
        self._last_total_volume = total_volume

        # 同一分钟
        if bar_time == self._last_bar_time:
            self._current_bar['high'] = max(self._current_bar['high'], price)
            self._current_bar['low'] = min(self._current_bar['low'], price)
            self._current_bar['close'] = price
            self._current_bar['volume'] += minute_volume
            return None

        # 新分钟，完成旧bar
        completed_bar = (
            self._current_bar['time'],
            self._current_bar['open'],
            self._current_bar['high'],
            self._current_bar['low'],
            self._current_bar['close'],
            self._current_bar['volume'],
            0.0
        )

        self._bars.append(completed_bar)

        self.logger.info(
            f"K线完成 "
            f"{completed_bar[0]} "
            f"O:{completed_bar[1]} "
            f"H:{completed_bar[2]} "
            f"L:{completed_bar[3]} "
            f"C:{completed_bar[4]}"
        )

        # 开启新bar
        self._current_bar = {
            'time': bar_time,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': minute_volume
        }
        self._last_bar_time = bar_time
        # 直接push
        self._push_bar(completed_bar)
        return True
