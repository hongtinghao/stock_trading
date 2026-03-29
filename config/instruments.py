"""
合约/标的配置文件
定义交易标的的基本信息：代码、名称、交易所、手续费等
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
from pathlib import Path

from config.settings import settings


@dataclass
class Instrument:
    """交易标的信息"""

    # 基本信息
    symbol: str  # 代码，如 "000001.SZ"
    name: str  # 名称，如 "平安银行"
    market: str  # 市场，如 "SZ"（深市）
    exchange: str  # 交易所，如 "SZSE"

    # 交易参数
    currency: str = "CNY"  # 货币，默认人民币
    price_tick: float = 0.01  # 最小价格变动单位
    multiplier: float = 1.0  # 乘数（股票为1，期货可能不同）
    margin_rate: float = 1.0  # 保证金率（股票为1）

    # 费用参数
    commission_rate: float = 0.0003  # 佣金费率（万分之三）
    min_commission: float = 5.0  # 最低佣金（5元）
    stamp_duty_rate: float = 0.001  # 印花税率（千分之一，卖出时收）

    # 风险参数
    price_limit: float = 0.1  # 涨跌停板幅度（10%）
    is_st: bool = False  # 是否为ST股票
    is_suspended: bool = False  # 是否停牌

    # 衍生信息
    industry: Optional[str] = None  # 行业
    market_cap: Optional[float] = None  # 市值

    def __post_init__(self):
        """初始化后验证"""
        if not self.symbol:
            raise ValueError("标的代码不能为空")

        # 确保佣金费率合理
        if self.commission_rate <= 0:
            raise ValueError("佣金费率必须大于0")

        # 根据市场设置默认参数
        if self.market in ["SH", "SZ"]:
            self.price_tick = 0.01
        elif self.market in ["HK"]:
            self.price_tick = 0.01
            self.currency = "HKD"

    @property
    def full_name(self) -> str:
        """完整名称：代码 + 名称"""
        return f"{self.symbol} {self.name}"

    @property
    def is_a_share(self) -> bool:
        """是否为A股"""
        return self.market in ["SH", "SZ"]

    def calculate_commission(self, price: float, volume: float) -> float:
        """计算佣金"""
        commission = price * volume * self.commission_rate
        return max(commission, self.min_commission)

    def calculate_stamp_duty(self, price: float, volume: float) -> float:
        """计算印花税（仅卖出时）"""
        return price * volume * self.stamp_duty_rate


class InstrumentManager:
    """标的管理器"""
    def __init__(self):
        self.instruments: Dict[str, Instrument] = {}

    def add_instrument(self, instrument: Instrument):
        """添加标的"""
        self.instruments[instrument.symbol] = instrument

    def get_instrument(self, symbol: str) -> Instrument:
        """获取标的信息"""
        if symbol not in self.instruments:
            # 如果不存在，创建默认标的
            market = "SZ" if symbol.endswith(".SZ") else "SH" if symbol.endswith(".SH") else "UNKNOWN"
            instrument = Instrument(
                symbol=symbol,
                name=symbol,
                market=market,
                exchange="UNKNOWN",
            )
            self.add_instrument(instrument)

        return self.instruments[symbol]

    def get_all_symbols(self) -> List[str]:
        """获取所有标的代码"""
        return list(self.instruments.keys())

    def get_a_share_symbols(self) -> List[str]:
        """获取A股标的代码"""
        return [s for s in self.instruments.keys()
                if self.instruments[s].is_a_share and not self.instruments[s].symbol.endswith("SH")]

    def get_etf_symbols(self) -> List[str]:
        """获取ETF标的代码"""
        return [s for s in self.instruments.keys()
                if "ETF" in self.instruments[s].name]

    def save_to_file(self, filepath: Optional[Path] = None):
        """保存到文件"""
        if filepath is None:
            filepath = settings.DATA_PROCESSED_DIR / "instruments.json"

        data = {
            symbol: {
                "name": instr.name,
                "market": instr.market,
                "exchange": instr.exchange,
                "currency": instr.currency,
                "price_tick": instr.price_tick,
                "commission_rate": instr.commission_rate,
            }
            for symbol, instr in self.instruments.items()
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, filepath: Optional[Path] = None):
        """从文件加载"""
        if filepath is None:
            filepath = settings.DATA_PROCESSED_DIR / "instruments.json"

        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for symbol, info in data.items():
                self.add_instrument(Instrument(
                    symbol=symbol,
                    **info
                ))


# 创建全局管理器实例
instrument_manager = InstrumentManager()