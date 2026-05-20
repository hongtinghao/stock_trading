from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(4), nullable=False)   # BUY/SELL
    price = Column(Float, nullable=False)
    size = Column(Integer, nullable=False)
    order_ref = Column(String(50))
    status = Column(String(20), default='SUBMITTED')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class AccountSnapshot(Base):
    # 时间更新
    __tablename__ = 'account_snapshots'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    cash = Column(Float)
    total_value = Column(Float)
    positions = Column(Text)   # JSON string

class StrategyLog(Base):
    # 账户快照
    __tablename__ = 'strategy_logs'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    strategy = Column(String(50))
    level = Column(String(20))
    message = Column(Text)