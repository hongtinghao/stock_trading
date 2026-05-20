from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config.settings import settings

# 单例模式持有引擎和会话工厂
_engine = None
_Session = None

def get_engine():
    global _engine
    if _engine is None:
        db_url = settings.DATABASE_URL
        _engine = create_engine(db_url, echo=False, pool_pre_ping=True)
    return _engine

def get_session():
    global _Session
    if _Session is None:
        engine = get_engine()
        _Session = scoped_session(sessionmaker(bind=engine))
    return _Session()

def init_db():
    # 创建所有表
    from db.models import Base
    engine = get_engine()
    Base.metadata.create_all(engine)