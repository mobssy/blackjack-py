"""
JackPy - 데이터베이스 베이스 설정
SQLAlchemy Base 및 Session 관리
"""

import os
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.ext.declarative import declared_attr
from contextlib import contextmanager
from typing import Generator

# Database URL from environment variable
# 기본값: SQLite (로컬 개발용)
# CI/Production: PostgreSQL (환경변수로 오버라이드)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jackpy.db")

# SQLAlchemy 엔진 생성
# SQLite의 경우 pool 설정 무시
engine_kwargs = {
    "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
}

# PostgreSQL인 경우에만 pool 설정 추가
if DATABASE_URL.startswith("postgresql"):
    engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,  # 연결 유효성 검사
        }
    )

engine = create_engine(DATABASE_URL, **engine_kwargs)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스
Base = declarative_base()


class TimestampMixin:
    """타임스탬프 자동 관리 Mixin"""

    @declared_attr
    def created_at(cls):
        from sqlalchemy import Column, DateTime

        return Column(DateTime, default=datetime.utcnow, nullable=False)

    @declared_attr
    def updated_at(cls):
        from sqlalchemy import Column, DateTime

        return Column(
            DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
        )


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션 컨텍스트 매니저

    사용 예:
        with get_db() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """데이터베이스 테이블 초기화"""
    from models.user import User
    from models.group import Group
    from models.round import Round
    from models.approval import Approval
    from models.ad_schedule import AdSchedule

    Base.metadata.create_all(bind=engine)

    # 기존 DB에 language 컬럼이 없으면 추가 (SQLite 마이그레이션)
    with engine.connect() as conn:
        try:
            conn.execute(
                __import__('sqlalchemy').text(
                    "ALTER TABLE users ADD COLUMN language VARCHAR(2) NOT NULL DEFAULT 'ko'"
                )
            )
            conn.commit()
        except Exception:
            pass  # 이미 컬럼이 있으면 무시

    print("✅ 데이터베이스 테이블 초기화 완료")


def drop_db() -> None:
    """데이터베이스 테이블 삭제 (주의!)"""
    Base.metadata.drop_all(bind=engine)
    print("⚠️  데이터베이스 테이블 삭제 완료")
