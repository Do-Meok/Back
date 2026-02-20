import asyncio
import sys
import importlib
import pkgutil
from pathlib import Path

from sqlalchemy.ext.asyncio import async_engine_from_config

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))

from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from alembic import context

from core.config import settings
from core.database import Base
import domains


def import_all_models():
    """domains 패키지 내의 모든 models 모듈을 동적으로 임포트합니다."""
    # domains 폴더 내의 모든 서브 패키지(user, ingredient 등)를 순회
    for loader, module_name, is_pkg in pkgutil.walk_packages(domains.__path__, domains.__name__ + "."):
        # 모듈 이름에 'models'가 포함되어 있다면 임포트
        if "models" in module_name:
            importlib.import_module(module_name)
            print(f"📦 Auto-discovered model: {module_name}")


config = context.config

config.set_main_option("sqlalchemy.url", settings.POSTGRES_DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import_all_models()
print(f"✅ Registered Tables: {list(Base.metadata.tables.keys())}")
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline 모드: DB 연결 없이 SQL 파일만 생성할 때"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """실제 마이그레이션을 실행하는 동기 함수 (run_sync 내에서 호출됨)"""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Online 모드: 실제 DB에 접속하여 마이그레이션 실행"""
    print(f"DEBUG: Connecting to {settings.POSTGRES_DATABASE_URL}")
    # 비동기 엔진 생성
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # 핵심: 비동기 연결 상태에서 동기 마이그레이션 로직을 실행함
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# --- 실행부 ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    # asyncio.run을 사용하여 비동기 함수 실행
    try:
        asyncio.run(run_migrations_online())
    except (RuntimeError, DeprecationWarning):
        # 이미 루프가 돌아가고 있는 환경(일부 IDE 등) 대응
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_migrations_online())
