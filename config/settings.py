"""
全局参数配置文件
这里定义了整个项目的全局参数，包括路径、回测参数、数据源配置等
"""
import os
from pathlib import Path
from datetime import datetime


class Settings:
    """全局配置类"""

    # 项目路径配置
    BASE_DIR = Path(__file__).parent.parent  # 项目根目录

    # 数据目录
    DATA_DIR = BASE_DIR / "data"
    DATA_RAW_DIR = DATA_DIR / "raw"  # 原始数据
    DATA_PROCESSED_DIR = DATA_DIR / "processed"  # 处理后的数据

    # 结果目录
    RESULTS_DIR = BASE_DIR / "results"
    BACKTEST_LOGS_DIR = RESULTS_DIR / "backtest_logs"  # 回测日志
    EQUITY_CURVES_DIR = RESULTS_DIR / "equity_curves"  # 资金曲线图
    TRADES_DIR = RESULTS_DIR / "trades"  # 交易明细
    PERFORMANCE_REPORTS_DIR = RESULTS_DIR / "performance_reports"  # 绩效报告

    # 回测参数配置
    BACKTEST_CONFIG = {
        # 资金管理
        'INITIAL_CASH': 100000.0,  # 初始资金（元）
        'COMMISSION': 0.001,  # 佣金费率（千分之一）
        'SLIPPAGE': 0.001,  # 滑点（千分之一）

        # 交易设置
        'TRADE_SIZE': 100,  # 每手交易数量
        'MIN_TRADE_SIZE': 100,  # 最小交易单位
        'ALLOW_SHORT': False,  # 是否允许做空

        # 风险控制
        'MAX_POSITION_SIZE': 0.8,  # 最大仓位比例
        'STOP_LOSS_ENABLED': True,  # 启用止损
        'TAKE_PROFIT_ENABLED': True,  # 启用止盈
    }
    '''
    # 5. 策略配置
    STRATEGY_CONFIG = {
        'DEFAULT_TIMEFRAME': 'daily',  # 默认时间框架：daily, weekly, monthly
        'DEFAULT_LOOKBACK': 252,  # 默认回看周期（交易日）
        'OPTIMIZATION_METHOD': 'grid',  # 优化方法：grid, random, bayesian
    }
    '''

    # 数据源配置
    DATA_SOURCES = {
        'active': 'baostock',  # 当前使用的数据源: 'akshare', 'baostock'
        'akshare': {
            'enabled': True,
            'save_local': True,  # 是否保存到本地
            'update_interval': 86400,  # 更新间隔（秒）
            'retry': 3,  # 失败重试次数
            'timeout': 10,  # 请求超时（秒）
            'proxy': None,  # 代理地址，如 'http://127.0.0.1:10809'
        },
        'baostock': {
            'enabled': True,
            'save_local': True,
            'username': '',
            'password': '',
            'retry': 3,
            'timeout': 10,
        },
    }

    # 日志配置
    LOGGING_CONFIG = {
        'DIR': BASE_DIR / 'logs',  # 日志目录
        'FILE_NAME': 'quant.log',  # 日志文件名
        'CONSOLE_LEVEL': os.getenv('LOG_CONSOLE_LEVEL', 'INFO'),
        'FILE_LEVEL': os.getenv('LOG_FILE_LEVEL', 'DEBUG'),
        'WHEN': 'midnight',  # 滚动周期：midnight / H / D / W0
        'INTERVAL': 1,  # 滚动间隔
        'BACKUP_COUNT': 14,  # 保留备份数
        'CONSOLE_FORMAT': '[%(asctime)s] %(levelname)-5s | %(name)s | %(message)s',
        'CONSOLE_DATE_FORMAT': '%H:%M:%S',
        'FILE_FORMAT': '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
    }

    # 可视化配置
    PLOTTING_CONFIG = {
        'STYLE': 'seaborn-v0_8-whitegrid',  # 图表风格
        'FIG_SIZE': (16, 10),  # 图表大小
        'DPI': 100,  # 图片分辨率
        'SAVE_FORMAT': 'png',  # 保存格式：png, pdf, svg
        'SHOW_GRID': True,  # 显示网格
        'SHOW_LEGEND': True,  # 显示图例
    }

    # 模型配置
    MODEL_CONFIG = {
        'provider': 'zhipu',
        'api_key': '346674b79dc848b09ccd51b48da258b6.ehYZRlunh0fMGnus',
        'model_name': 'glm-4-plus',
        'timeout': 10,
        'retries': 5,
        'cache_enabled': True,
        'cache_path': 'stock_trading/data/processed/model_cache.db'
    }

    # 新闻数据源配置
    NEWS_SOURCE = {
        'source': 'api',  # 'local' 或 'api'
        'base_path': 'stock_trading/data/raw/news',
        'file_pattern': '{symbol}_news.csv'
    }


    @classmethod
    def init_directories(cls):
        """初始化所有需要的目录"""
        dirs = [
            cls.DATA_RAW_DIR,
            cls.DATA_PROCESSED_DIR,
            cls.BACKTEST_LOGS_DIR,
            cls.EQUITY_CURVES_DIR,
            cls.TRADES_DIR,
            cls.PERFORMANCE_REPORTS_DIR,
        ]

        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"创建目录: {directory}")

    @classmethod
    def get_today_str(cls):
        """获取当前日期字符串"""
        return datetime.now().strftime('%Y%m%d')


# 创建配置实例
settings = Settings()

# 初始化目录（在导入时自动创建）
settings.init_directories()