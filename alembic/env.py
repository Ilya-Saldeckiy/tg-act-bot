from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

# Импортируйте ваш Base и модели
from core.models import Base

# Это объект метаданных, который Alembic будет использовать для генерации миграций
target_metadata = Base.metadata

# Настройка логгера
config = context.config
fileConfig(config.config_file_name)

def run_migrations_offline():
    """Запуск миграций в offline-режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Запуск миграций в online-режиме."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()