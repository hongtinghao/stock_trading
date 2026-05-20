"""
同花顺实盘 Broker
"""

import time
import threading
from datetime import datetime
import backtrader as bt
import easytrader
import pyautogui

from utils.logger import get_logger
from backtrader.order import BuyOrder, SellOrder

class THSLiveBroker(bt.BrokerBase):
    """同花顺实盘交易"""

    params = (
        ('exe_path', ''),
        ('account', ''),
        ('password', ''),
        ('commission', 0.00025),
        # ('sync_interval', 5),  # 账户同步
    )

    def __init__(self, redis_client=None, db_repo=None, **kwargs):
        super().__init__(**kwargs)
        self.logger = get_logger('THSLiveBroker')
        self.user = None
        self.redis = redis_client
        self.db_repo = db_repo
        self._cash = 0.0
        self._value = 0.0
        self.startingcash = 0.0
        self._positions = {}
        self._order_map = {}
        self._orders = {}
        self._pending_orders = []
        self._lock = threading.Lock()
        # self._last_sync_ts = 0
        # self._running = False


    # Broker 生命周期
    def start(self):

        try:
            self.logger.info("正在连接同花顺客户端...")
            self.user = easytrader.use('ths')
            self.user.connect(self.p.exe_path)
            # 如需自动登录
            # self.user.prepare(self.p.account, self.p.password)
            self.logger.info("同花顺连接成功")
            # 初始同步
            self._sync_account_safe(force=True)
            # 启动订单监听
            # self._running = True
            # threading.Thread(target=self._order_watcher, daemon=True).start()
            self.startingcash = self._value
            self.logger.info( f"账户初始化完成 cash={self._cash}, value={self._value}")
        except Exception as e:
            self.logger.exception(f"Broker启动失败: {e}")
            raise

    def stop(self):
        # self._running = False
        self.logger.info("Broker stop")

    # 账户同步
    def _sync_account_safe(self, force=False):
        now = time.time()
        # 限制同步频率
        # if not force:
        #     if now - self._last_sync_ts < self.p.sync_interval:
        #         return
        try:
            self._sync_account()
            # self._last_sync_ts = now
        except Exception as e:
            self.logger.error(f"账户同步失败: {e}")

    def _sync_account(self):
        if self.user is None:
            return
        with self._lock:
            balance = self.user.balance
            if balance:
                self._cash = float(balance.get('可用金额', 0))
                self._value = float(balance.get('总资产', 0))
            time.sleep(2)
            positions = self.user.position
            new_positions = {}
            for pos in positions:
                code = pos.get('证券代码')
                if not code:
                    continue
                new_positions[code] = {
                    'size': int(pos.get('股票余额', 0)),
                    'price': float(pos.get('成本价', 0)),
                }

            self._positions = new_positions
            if self.db_repo:
                try:
                    self.db_repo.save_account_snapshot(self._cash, self._value, self._positions)
                except Exception as e:
                    self.logger.error(f"保存账户快照失败: {e}")

    def getcash(self):
        # self._sync_account_safe()
        return self._cash

    def getvalue(self, datas=None):
        # self._sync_account_safe()
        return self._value

    def getposition(self, data):
        symbol = self._get_symbol(data).split('.')[0]
        pos = self._positions.get(symbol,{'size': 0, 'price': 0.0})
        return bt.Position(size=pos['size'], price=pos['price'])


    # 订单通知
    def notify(self, order):
        self._pending_orders.append(order.clone())

    def get_notification(self):
        if self._pending_orders:
            return self._pending_orders.pop(0)
        return None

    def buy(self, owner, data, size, price=None, exectype=None, **kwargs):
        return self._place_order( owner, data, bt.Order.Buy, size, price, exectype)

    def sell(self, owner, data, size, price=None, exectype=None, **kwargs):
        return self._place_order(owner, data, bt.Order.Sell, size, price, exectype)

    # 撤单
    def cancel(self, order):
        try:
            entrust_no = self._order_map.get(order.ref)
            if not entrust_no:
                order.cancel()
                self.notify(order)
                return

            self.user.cancel_entrust(entrust_no)
            order.cancel()
            self.notify(order)
            self.logger.info(f"撤单成功: {entrust_no}")

        except Exception as e:
            self.logger.error(f"撤单失败: {e}")

    # 下单
    def _place_order(self, owner, data, side, size, price=None, exectype=None):
        # 下单前同步一次账户
        self._sync_account_safe(force=True)
        symbol = self._get_symbol(data).split('.')[0]
        # 价格
        if exectype == bt.Order.Limit and price:
            use_price = price
        else:
            use_price = round(float(data.close[0]), 2)
        # 创建订单对象
        if side == bt.Order.Buy:

            order = BuyOrder(
                owner=owner,
                data=data,
                size=size,
                price=use_price,
                exectype=bt.Order.Market,
            )

        else:
            order = SellOrder(
                owner=owner,
                data=data,
                size=size,
                price=use_price,
                exectype=bt.Order.Market,
            )
        # 限流
        # if self.redis:
        #     limited = self.redis.is_rate_limited(f"trade:{symbol}", limit=5, window_sec=60)
        #     if limited:
        #         self.logger.warning(f"交易限流: {symbol}")
        #         order.reject()
        #         self._pending_orders.append(order)
        #         return order


        # 下单
        try:
            self.logger.info( f"[下单] {symbol} {side} size={size} price={use_price}")
            if side == bt.Order.Buy:
                # 定位
                result = self.user.buy(symbol, price=use_price, amount=int(size))
                self.pyautogui_operation(symbol, use_price, amount=size, operation="buy")
            else:
                result = self.user.sell(symbol, price=use_price, amount=int(size))
                self.pyautogui_operation(symbol, use_price, amount=size, operation="sell")
            self.logger.info(f"券商返回: {result}")
            # entrust_no = (result.get('entrust_no') or result.get('订单号') or '')
            # with self._lock:
            #     self._order_map[order.ref] = entrust_no
            #     self._orders[order.ref] = order
            #
            # 下单前持仓
            before_pos = self._positions.get(symbol, {}).get('size', 0)
            # 提交订单状态
            order.addcomminfo(self.getcommissioninfo(data))
            order.submit(self)
            order.accept(self)
            self.notify(order)


            # ===== 等待成交 =====
            timeout = 30
            start_ts = time.time()

            while True:
                time.sleep(10)
                # self._sync_account_safe(force=True)
                now_pos = self._positions.get(symbol, {}).get('size', 0)
                # 买入成交
                if side == bt.Order.Buy:
                    if now_pos > before_pos:
                        dt = bt.date2num(datetime.now())
                        order.execute(
                            dt=dt,
                            size=size,
                            price=use_price,
                            closed=0,
                            closedvalue=0,
                            closedcomm=0,
                            opened=size,
                            openedvalue=use_price * size,
                            openedcomm=0,
                            margin=0,
                            pnl=0,
                            psize=now_pos,
                            pprice=use_price
                        )
                        order.completed()
                        self.logger.info(f"[买入成交] {symbol}")
                        return order
                # 卖出成交
                else:
                    if now_pos < before_pos:
                        dt = bt.date2num(datetime.now())
                        order.execute(
                            dt=dt,
                            size=size,
                            price=use_price,
                            closed=size,
                            closedvalue=use_price * size,
                            closedcomm=0,
                            opened=0,
                            openedvalue=0,
                            openedcomm=0,
                            margin=0,
                            pnl=0,
                            psize=now_pos,
                            pprice=use_price
                        )
                        order.completed()
                        self.logger.info(f"[卖出成交] {symbol}")
                        return order

                # 超时撤单
                elapsed = time.time() - start_ts
                if elapsed > timeout:
                    self.logger.warning(f"[超时未成交] {symbol} -> 撤单")
                    try:
                        # 定位
                        self.user.buy(symbol, price=use_price, amount=int(size))
                        self.pyautogui_withdraw()
                        order.cancel()
                        self.notify(order)
                        self.logger.info(f"[撤单成功] {symbol}")

                    except Exception as e:
                        self.logger.error(f"[撤单失败] {e}")
                    return order
            # filled = False
            # for i in range(3):
            #     time.sleep(5)
            #     try:
            #         entrusts = self.user.today_entrusts
            #         for e in entrusts:
            #             eno = str(e.get('entrust_no') or e.get('委托编号') or '')
            #             if eno != str(entrust_no):
            #                 continue
            #             status = str(e.get('status') or e.get('状态') or '')
            #
            #             # 成交
            #             if status in ['已成', '全部成交', '已成交']:
            #                 filled = True
            #                 price = float(e.get('成交价') or 0)
            #                 size = int(e.get('成交数量') or 0)
            #                 dt = bt.date2num(datetime.now())
            #                 order.execute(
            #                     dt=dt,
            #                     size=size,
            #                     price=price,
            #                     closed=0,
            #                     closedvalue=0,
            #                     closedcomm=0,
            #                     opened=size,
            #                     openedvalue=price * size,
            #                     openedcomm=0,
            #                     margin=0,
            #                     pnl=0,
            #                     psize=size,
            #                     pprice=price
            #                 )
            #                 order.completed()
            #                 self.logger.info(f"[成交确认] {entrust_no}")
            #                 return order
            #
            #             # 已撤
            #             if status in ['已撤', '已撤单']:
            #                 order.cancel()
            #                 self.logger.info(f"[撤单确认] {entrust_no}")
            #                 return order
            #
            #     except Exception as e:
            #         self.logger.error(f"确认失败: {e}")
            #
            # # 强制撤单
            # if not filled:
            #     try:
            #         if entrust_no:
            #             self.user.cancel_entrust(entrust_no)
            #             self.logger.info(f"[超时撤单] {entrust_no}")
            #     except Exception as e:
            #         self.logger.error(f"撤单失败: {e}")
            #     order.cancel()
            #     return order

        except Exception as e:
            self.logger.exception(f"下单失败: {e}")
            order.reject()
            return order

    def pyautogui_withdraw(self):
        pyautogui.press('f3')
        time.sleep(1)
        pyautogui.press('down')
        time.sleep(0.3)
        pyautogui.press('enter')
        time.sleep(0.5)
        pyautogui.press('enter')

    def pyautogui_operation(self, symbol, price, amount, operation):
        time.sleep(0.3)
        if operation == "buy":
            pyautogui.press('backspace')
            pyautogui.typewrite(symbol)
            pyautogui.press('enter')
            time.sleep(0.3)
            pyautogui.press('backspace')
            time.sleep(0.5)
            pyautogui.press('backspace')
            time.sleep(0.3)
            pyautogui.press('backspace')
            time.sleep(0.3)
            pyautogui.press('backspace')
            time.sleep(0.3)
            pyautogui.typewrite(str(price))
            pyautogui.press('enter')
            time.sleep(0.3)
            pyautogui.typewrite(str(amount))
            pyautogui.press('enter')
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(0.3)
            pyautogui.press('enter')

        if operation == "sell":
            pyautogui.press('backspace')
            pyautogui.typewrite(symbol)
            pyautogui.press('enter')
            time.sleep(0.3)
            pyautogui.press('backspace')
            time.sleep(0.5)
            pyautogui.press('backspace')
            time.sleep(0.3)
            pyautogui.press('backspace')
            time.sleep(0.3)
            pyautogui.press('backspace')
            time.sleep(0.3)
            pyautogui.typewrite(str(price))
            pyautogui.press('enter')
            time.sleep(0.3)
            pyautogui.typewrite(str(amount))
            pyautogui.press('enter')
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(0.3)
            pyautogui.press('enter')

    # 订单回报线程
    # def _order_watcher(self):
    #     self.logger.info("订单回报线程启动")
    #     while self._running:
    #         try:
    #             if not self.user:
    #                 time.sleep(1)
    #                 continue
    #
    #             # 同步账户
    #             self._sync_account()
    #             entrusts = self.user.today_entrusts
    #
    #             for order_ref, entrust_no in list(self._order_map.items()):
    #                 if not entrust_no:
    #                     continue
    #
    #                 order = self._orders.get(order_ref)
    #                 if not order:
    #                     continue
    #
    #                 # 已完成订单不重复处理
    #                 if order.status in [order.Completed,order.Canceled, order.Rejected]:
    #                     continue
    #
    #                 for e in entrusts:
    #                     eno = (e.get('entrust_no')or e.get('委托编号')or '')
    #                     if str(eno) != str(entrust_no):
    #                         continue
    #                     status = str(e.get('status') or e.get('状态') or '')
    #
    #                     # 已成交
    #                     if status in ['已成', '全部成交', '已成交']:
    #                         price = float(e.get('成交价') or e.get('price') or 0)
    #                         size = int(e.get('成交数量') or e.get('amount') or 0)
    #                         dt = bt.date2num(datetime.now())
    #                         order.execute(
    #                             dt=dt,
    #                             size=size,
    #                             price=price,
    #                             closed=0,
    #                             closedvalue=0,
    #                             closedcomm=0,
    #                             opened=size,
    #                             openedvalue=price * size,
    #                             openedcomm=0,
    #                             margin=0,
    #                             pnl=0,
    #                             psize=size,
    #                             pprice=price
    #                         )
    #                         order.completed()
    #                         self.notify(order)
    #                         self.logger.info(f"[成交] {entrust_no} price={price} size={size}")
    #                         # 删除映射
    #                         self._order_map.pop(order_ref, None)
    #                         self._orders.pop(order_ref, None)
    #
    #
    #                     # 已撤单
    #                     elif status in ['已撤', '已撤单']:
    #                         order.cancel()
    #                         self.notify(order)
    #                         self.logger.info(f"[撤单回报] {entrust_no}")
    #                         self._order_map.pop(order_ref, None)
    #                         self._orders.pop(order_ref, None)
    #
    #         except Exception as e:
    #             self.logger.error(f"订单回报异常: {e}")
    #         time.sleep(1)

    # 工具
    def _get_symbol(self, data):
        if hasattr(data, '_name') and data._name:
            return data._name
        if hasattr(data, 'p') and hasattr(data.p, 'symbol'):
            return data.p.symbol
        return ''