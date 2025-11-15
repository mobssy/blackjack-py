"""
JackPy - Alembic Environment
데이터베이스 마이그레이션 환경 설정
"""
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Alembic Config 객체
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 모델 메타데이터 import
from models.base import Base
from models.user import User
from models.group import Group
from models.round import Round
from models.approval import Approval
from models.ad_schedule import AdSchedule

target_metadata = Base.metadata

# 데이터베이스 URL 설정 (환경변수에서)
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/jackpy")
)


def run_migrations_offline() -> None:
    """
    오프라인 모드에서 마이그레이션 실행

    'offline' 모드는 SQL을 생성하지만 실제 데이터베이스에 연결하지 않습니다.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    온라인 모드에서 마이그레이션 실행

    실제 데이터베이스 연결을 생성하여 마이그레이션을 수행합니다.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
