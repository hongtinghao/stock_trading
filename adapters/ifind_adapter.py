"""
iFinD 数据适配器
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any


try:
    from iFinDPy import (
        THS_iFinDLogin, THS_HistoryQuotes, THS_RealtimeQuotes,
        THS_BasicData, THS_DateSequence, THS_WC
    )

    IFIND_AVAILABLE = True
except ImportError:
    IFIND_AVAILABLE = False
    raise ImportError("请安装 iFinDPy: pip install iFinDPy 或联系同花顺获取SDK")


class IFindAdapter:
    """iFinD数据适配器"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.connected = False
        self._login()

    def _login(self):
        # 登录iFinD
        result = THS_iFinDLogin(self.username, self.password)
        if result == 0:
            self.connected = True
            print("✅ iFinD登录成功")
        else:
            raise ConnectionError(f"iFinD登录失败，错误码: {result}")

    def _format_code(self, symbol: str) -> str:
        # 转换代码格式
        if '.' in symbol:
            return symbol.upper()
        code = symbol
        if code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith('0') or code.startswith('3'):
            return f"{code}.SZ"
        elif code.startswith('8') or code.startswith('4'):
            return f"{code}.BJ"
        return f"{code}.SZ"

    def get_history_data(self, symbol: str, start_date: str, end_date: str, period: str = "D") -> pd.DataFrame:
        # 历史行情
        if not self.connected:
            raise ConnectionError("iFinD未连接")
        ifind_code = self._format_code(symbol)
        fields = ("open,high,low,close,volume,amount,ps,pcf,ths_trading_status_stock,preClose,avgPrice,change,changeRatio,"
                  "max_up,max_down,turnoverRatio,transactionAmount,totalShares,totalCapital,"
                  "floatSharesOfAShares,floatSharesOfBShares,floatCapitalOfAShares,floatCapitalOfBShares,pe_ttm,pe,pb,"
                  "ths_up_and_down_status_stock,ths_vol_after_trading_stock,ths_trans_num_after_trading_stock,"
                  "ths_amt_after_trading_stock,ths_vaild_turnover_stock,adjustmentFactorBackward1")
        data = THS_HistoryQuotes(ifind_code, fields, f"period:{period}", start_date, end_date)
        if isinstance(data, dict) and data.get('errorcode') == 0:
            table = data['tables'][0]['table']
            dates = data['tables'][0]['time']
            df = pd.DataFrame(table)
            df['date'] = pd.to_datetime(dates)
            df.set_index('date', inplace=True)
            return df
        else:
            return pd.DataFrame()

    def get_realtime_quote(self, symbol: str) -> Optional[Dict]:
            # 实时行情
            if not self.connected:
                raise ConnectionError("iFinD未连接")
            ifind_code = self._format_code(symbol)
            fields = ("tradeDate,opreClose,open,high,low,latest,latesAtmount,latestVolume,avgPrice,"
                      "change,changeRatio,upperLimit,downLimit,amount,volume,turnoverRatio,sellVolume,buyVolume,"
                      "totalBidVol,totalAskVol,totalShares,totalCapital,pd,riseDayCount,suspensionFlag,tradeStatus,"
                      "chg_1min,chg_3min,chg_5min,chg_5d,chg_10d,chg_20d,chg_60d,chg_120d,chg_250d,chg_year,"
                      "mv,vol_ratio,committee,commission_diff,pe_ttm,pbr_lf,swing,latest_price,af_backward"
            )
            data =  THS_RealtimeQuotes(ifind_code, fields,"")
            if isinstance(data, dict) and data.get('errorcode') == 0:
                table = data['tables'][0]['table']
                dates = data['tables'][0]['time']
                df = pd.DataFrame(table)
                df['date'] = pd.to_datetime(dates)
                df.set_index('date', inplace=True)
                return df
            else:
                return pd.DataFrame()


    def get_basic_data(self, symbol: str, params: list) -> pd.DataFrame:
        # 基本面数据
        if not self.connected:
            raise ConnectionError("iFinD未连接")
        ifind_code = self._format_code(symbol)
        if len(params) > 1:
            fields, other_type = params[0], params[1]
            result = THS_BasicData(ifind_code, fields, other_type)
        else:
            result = THS_BasicData(ifind_code, params[0], "")
        if isinstance(result, dict) and result.get('errorcode') == 0:
            item = result['tables'][0]
            thscode = item['thscode']
            table_dict = item['table']
            df = pd.DataFrame(table_dict)
            df['thscode'] = thscode
            df.set_index('thscode', inplace=True)
            return df
        return pd.DataFrame()

    # def get_date_sequence(self, symbol: str, indicators: str, params: list, start_date: str,end_date: str) -> pd.DataFrame:
    #     # 日期序列数据
    #     if not self.connected:
    #         raise ConnectionError("iFinD未连接")
    #     ifind_code = self._format_code(symbol)
    #     fields, other_type = params[0], params[1]
    #     result = THS_DateSequence(ifind_code, fields, other_type, start_date, end_date)
    #     if isinstance(result, dict) and result.get('errorcode') == 0:
    #         tables = result.get('tables', [])
    #         if tables and len(tables) > 0:
    #             return pd.DataFrame(tables[0])
    #     return pd.DataFrame()


    # def get_search_info(self, query: str, domain: str = "stock") -> pd.DataFrame:
    #     # 智能搜索（问财）
    #     if not self.connected:
    #         raise ConnectionError("iFinD未连接")
    #     result = THS_WC(query, domain)
    #     # 检查返回类型并提取数据
    #     if isinstance(result, dict) and result.get('errorcode') == 0:
    #         tables = result.get('tables', [])
    #         if tables and len(tables) > 0:
    #             return pd.DataFrame(tables[0])
    #     return pd.DataFrame()


# 单例模式
_ifind_adapter = None


def get_ifind_adapter(username: str = None, password: str = None) -> IFindAdapter:
    # 获取iFinD适配器
    global _ifind_adapter
    if _ifind_adapter is None:
        from config.settings import settings
        config = settings.DATA_SOURCES['ifind']
        username = username or config.get('username')
        password = password or config.get('password')

        if not username or not password:
            raise ValueError("请在config/settings.py中配置iFinD账号密码")

        _ifind_adapter = IFindAdapter(username, password)

    return _ifind_adapter