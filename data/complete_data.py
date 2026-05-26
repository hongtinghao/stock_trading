"""
数据定义
Backtrader 的默认 PandasData 只读取 open, high, low, close, volume, openinterest
Backtrader要求lines中所有字段必须是数值（float/int）
"""

import backtrader as bt

class CompletePandasData(bt.feeds.PandasData):
    #支持全部 iFinD 字段的 Backtrader 数据类
    # 定义所有 lines（字段名，必须与 DataFrame 列名一致）
    lines = (
        # 历史数据
        'open', 'high', 'low', 'close', 'volume', 'amount', 'ps', 'pcf', 'pre_close', 'avg_price', 'change',
        'change_ratio','max_up', 'max_down', 'turnover_ratio', 'transaction_amount', 'total_shares',
        'total_capital', 'float_shares_of_a_shares', 'float_capital_of_a_shares', 'pe_ttm', 'pe', 'pb',
        'ths_vaild_turnover_stock', 'adjustment_factor_backward1',
        # 'ths_trading_status_stock', 'float_shares_of_b_shares', 'float_capital_of_b_shares', 'ths_up_and_down_status_stock',
        # 'ths_vol_after_trading_stock', 'ths_trans_num_after_trading_stock', 'ths_amt_after_trading_stock',
        # 时序数据
        'roe',
    )

    # 参数映射：指定 DataFrame 中对应的列名（默认与 line 同名）
    params = (
        # 历史数据
        ('datetime', None),      # 使用 DataFrame 的索引作为时间
        ('openinterest', -1),    # 无此列，设为 -1 忽略
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('amount', 'amount'),
        ('ps', 'ps'),
        ('pcf', 'pcf'),
        # ('ths_trading_status_stock', 'ths_trading_status_stock'),
        ('pre_close', 'pre_close'),
        ('avg_price', 'avg_price'),
        ('change', 'change'),
        ('change_ratio', 'change_ratio'),
        ('max_up', 'max_up'),
        ('max_down', 'max_down'),
        ('turnover_ratio', 'turnover_ratio'),
        ('transaction_amount', 'transaction_amount'),
        ('total_shares', 'total_shares'),
        ('total_capital', 'total_capital'),
        ('float_shares_of_a_shares', 'float_shares_of_a_shares'),
        # ('float_shares_of_b_shares', 'float_shares_of_b_shares'),
        ('float_capital_of_a_shares', 'float_capital_of_a_shares'),
        # ('float_capital_of_b_shares', 'float_capital_of_b_shares'),
        ('pe_ttm', 'pe_ttm'),
        ('pe', 'pe'),
        ('pb', 'pb'),
        # ('ths_up_and_down_status_stock', 'ths_up_and_down_status_stock'),
        # ('ths_vol_after_trading_stock', 'ths_vol_after_trading_stock'),
        # ('ths_trans_num_after_trading_stock', 'ths_trans_num_after_trading_stock'),
        # ('ths_amt_after_trading_stock', 'ths_amt_after_trading_stock'),
        ('ths_vaild_turnover_stock', 'ths_vaild_turnover_stock'),
        ('adjustment_factor_backward1', 'adjustment_factor_backward1'),
        # 时序数据
        ('roe', 'roe'),
    )