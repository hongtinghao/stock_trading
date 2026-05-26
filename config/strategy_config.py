# config/strategy_config.py

from strategies.sma_cross import SMACrossStrategy
from strategies.multi_factor_strategy import MultiFactorStrategy
from strategies.test_strategy import TestCycleStrategy

STRATEGY_CONFIG = {
    # 双均线策略
    'SMACross': {
        'class': SMACrossStrategy,
        'params': {
            'fast_period': 5,
            'slow_period': 10,
            'stop_loss': 0.05,
            'take_profit': 0.10,
        },
        'symbols': [
            '600110.SH',
            '002585.SZ'
        ],
        'start_date': '2025-04-08',
        'end_date': '2026-04-10',
    },

    # 多因子策略
    'MultiFactor': {
        'class': MultiFactorStrategy,
        'params': {
            'top_n': 5,
            'rebalance_days': 21,
            'stop_loss': -0.10,
        },
        'symbols': [
            '600110.SH',
            '002585.SZ',
            '600519.SH',
            '000858.SZ',
            '300750.SZ',
            '002594.SZ',
            '601318.SH',
            '600036.SH',
            # '601166.SH',
            # '000333.SZ',
            # '601888.SH',
            # '300059.SZ',
            # '002714.SZ',
            # '603259.SH',
            # '688981.SH',
            # '002415.SZ',
            # '300015.SZ',
            # '600276.SH',
            # '601012.SH',
            # '002475.SZ',
            # '300308.SZ',
            # '000001.SZ'
        ],
        'start_date': '2025-04-08',
        'end_date': '2026-04-10',
    },


    # 实盘联调测试(实盘采用的是单股，回测优化为多股)
    'TestCycle': {
        'class': TestCycleStrategy,
        'params': {
            'cycle': 5,
            'size': 100,
        },
        'symbols': [
            '002585.SZ'
        ],
        'start_date': '2025-04-08',
        'end_date': '2026-04-10',
    }
}