from db.session import get_session
from db.models import Trade, AccountSnapshot, StrategyLog
from datetime import datetime
import json

class TradeRepository:
    # 添加交易记录
    @staticmethod
    def insert(trade_dict):
        sess = get_session()
        trade = Trade(**trade_dict)
        sess.add(trade)
        sess.commit()
        return trade.id

    # 更新订单状态
    @staticmethod
    def update_status(order_ref, status):
        sess = get_session()
        trade = sess.query(Trade).filter_by(order_ref=order_ref).first()
        if trade:
            trade.status = status
            trade.updated_at = datetime.now()
            sess.commit()

class AccountRepository:
    # 保存账户快照
    @staticmethod
    def save_snapshot(cash, total_value, positions_dict):
        sess = get_session()
        snapshot = AccountSnapshot(
            cash=cash,
            total_value=total_value,
            positions=json.dumps(positions_dict)
        )
        sess.add(snapshot)
        sess.commit()

class LogRepository:
    # 记录策略日志
    @staticmethod
    def log(strategy, level, message):
        sess = get_session()
        log = StrategyLog(strategy=strategy, level=level, message=message)
        sess.add(log)
        sess.commit()