import backtrader as bt
import pandas as pd
import time
from datetime import datetime
from typing import Optional
from adapters.ifind_adapter import IFindAdapter

class THSRealtimeData(bt.DataBase):
    """基于 iFinD 实时行情的 DataFeed，合成分钟K线"""

    params = (
        ('symbol', ''),
        ('timeframe', bt.TimeFrame.Minutes),
        ('compression', 1),
        ('backfill_minutes', 60),   # 启动时回溯分钟数
    )

    def __init__(self, ifind_adapter: IFindAdapter, redis_client=None):
        self.adapter = ifind_adapter
        self.redis = redis_client
        self._last_close = None
        self._minute_bars = {}        # 缓存当前分钟K线
        self._current_minute = None
        self._historical_loaded = False

    def start(self):
        self._load_historical_bars()

    def _load_historical_bars(self):
        """加载最近的历史分钟K线，用于初始化指标"""
        if self._historical_loaded:
            return
        # 这里简单起见，可以加载最近N天的日线或调用历史分钟接口
        # 实盘时可以加载最近几个交易日的数据
        # 若没有历史分钟数据，也可以不加载，但指标会有延迟
        self._historical_loaded = True

    def _get_current_quote(self):
        """获取最新实时行情"""
        df = self.adapter.get_realtime_quote(self.p.symbol)
        if df is not None and not df.empty:
            # 转为字典
            record = df.iloc[-1].to_dict()
            # 写入Redis
            if self.redis:
                self.redis.set_quote(self.p.symbol, record, ttl=60)
            return record
        return None

    def _update_minute_bar(self, quote: dict) -> Optional[dict]:
        """更新分钟K线，如果K线完整则返回，否则返回None"""
        now = datetime.now()
        current_minute = now.replace(second=0, microsecond=0)
        price = quote.get('latest') or quote.get('latest_price')
        volume = quote.get('latestVolume', 0)

        if price is None:
            return None

        if self._current_minute != current_minute:
            # 分钟切换，保存上一根K线
            if self._current_minute is not None and self._current_minute in self._minute_bars:
                bar = self._minute_bars[self._current_minute]
                bar['datetime'] = self._current_minute
                # 重置当前分钟缓存
                self._minute_bars.pop(self._current_minute, None)
                return bar
            # 新分钟开始
            self._minute_bars[current_minute] = {
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume,
                'datetime': current_minute
            }
            self._current_minute = current_minute
            return None
        else:
            # 同一分钟，更新
            bar_data = self._minute_bars[current_minute]
            bar_data['high'] = max(bar_data['high'], price)
            bar_data['low'] = min(bar_data['low'], price)
            bar_data['close'] = price
            bar_data['volume'] += volume
            return None

    def _load(self):
        """Backtrader 数据加载接口，返回True表示有数据，False表示没有"""
        quote = self._get_current_quote()
        if quote is None:
            time.sleep(0.5)
            return None

        bar = self._update_minute_bar(quote)
        if bar is None:
            # 尚未形成完整K线，稍后重试
            time.sleep(0.5)
            return None

        # 填充 lines
        self.lines.datetime[0] = bt.date2num(bar['datetime'])
        self.lines.open[0] = bar['open']
        self.lines.high[0] = bar['high']
        self.lines.low[0] = bar['low']
        self.lines.close[0] = bar['close']
        self.lines.volume[0] = bar['volume']
        self.lines.openinterest[0] = 0
        return True