from __future__ import annotations

from typing import Iterator, Optional

import logging

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.engine import Engine

from config import CONFIG

_engine: Optional[Engine] = None


def _build_mysql_url() -> str:
    """从 CONFIG 构建 MySQL 连接 URL。"""
    host = CONFIG["DB_HOST"]
    port = CONFIG["DB_PORT"]
    user = CONFIG["DB_USER"]
    password = CONFIG["DB_PASSWORD"]
    db_name = CONFIG["DB_NAME"]

    return (
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}" f"?charset=utf8mb4"
    )


def get_engine() -> Engine:
    """获取全局 Engine（惰性初始化，后续复用）。"""
    global _engine
    if _engine is None:
        url = _build_mysql_url()
        logging.info(f"Creating engine for {url}")
        _engine = create_engine(
            url,
            echo=False,  # 如需打印 SQL，可改为 True
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    return _engine


def get_session() -> Session:
    """获取一个新的 Session，常用于 with 语法."""
    engine = get_engine()
    return Session(engine)


def session_scope() -> Iterator[Session]:
    """
    提供一个简单的 session 上下文管理器生成器用法：
    with session_scope() as s:
        s.exec(...)
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """
    初始化数据库（创建所有表）。
    在需要时手动调用，例如：
        from db import init_db
        init_db()
    """
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
