"""
实盘交易主入口
"""
import sys
import signal
import threading
import time
import backtrader as bt
from config.settings import settings
from adapters.ifind_adapter import get_ifind_adapter
from data.real_time_feed import THSRealtimeData
from brokers.ths_broker import THSLiveBroker
from cache.redis_client import RedisClient
from db.session import init_db
from db.repositories import TradeRepository, AccountRepository, LogRepository
from utils.logger import get_logger

from strategies.sma_cross import SMACrossStrategy
from strategies.test_strategy import TestCycleStrategy

class LiveTradingEngine:
    """实盘交易"""

    def __init__(self):
        self.logger = get_logger('LiveEngine')
        self.running = True
        self.cerebro = None
        self.redis = None
        self.db_repo = None

    def _setup(self):
        # 初始化所有组件
        # 数据库
        init_db()
        self.db_repo = type('Repo', (), {
            'insert_trade': staticmethod(TradeRepository.insert),
        'update_trade_status': staticmethod(TradeRepository.update_status),
        'save_account_snapshot': staticmethod(AccountRepository.save_snapshot),
        'log': staticmethod(LogRepository.log)
        })()

        # Redis
        self.redis = RedisClient(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD
        )

        # iFinD 适配器
        self.ifind = get_ifind_adapter()

        # Cerebro
        self.cerebro = bt.Cerebro(
            runonce=False,
            preload=False,
            quicknotify=True,  # 尽快传递订单通知
          # stdstats=False,  # 可选，减少不必要观察者
        )

        # 实时数据源
        data = THSRealtimeData(
            ifind_adapter=self.ifind,
            redis_client=self.redis,
            symbol= "002585.SZ"
        )
        self.cerebro.adddata(data)

        # 实盘 Broker
        broker = THSLiveBroker(
            exe_path=settings.THS_EXE_PATH,
            account=settings.THS_ACCOUNT,
            password=settings.THS_PASSWORD,
            commission=settings.COMMISSION,
            redis_client=self.redis,
            db_repo=self.db_repo
        )
        self.cerebro.broker = broker
        # self.cerebro.broker.start()

        # 策略
        # self.cerebro.addstrategy(SMACrossStrategy, fast_period=10, slow_period=30)
        self.cerebro.addstrategy(TestCycleStrategy, cycle=5, size=100)

        # 可选观察者
        self.cerebro.addobserver(bt.observers.Broker)
        self.cerebro.addobserver(bt.observers.Trades)
        self.logger.info("实盘引擎初始化完成")


    def run(self):
        self._setup()
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        def cerebro_thread():
            try:
                self.cerebro.run()  # 会一直运行直到 stop()
            except Exception as e:
                self.logger.error(f"Cerebro运行出错: {e}")
            finally:
                self.logger.info("Cerebro 线程结束")

        t = threading.Thread(target=cerebro_thread)
        t.start()
        t.join()  # 等待线程结束
        self.logger.info("实盘引擎已退出")

    def _signal_handler(self, signum, frame):
        self.logger.info("收到退出信号，正在停止...")
        if self.cerebro:
            self.cerebro.stop()

if __name__ == '__main__':
    engine = LiveTradingEngine()
    engine.run()