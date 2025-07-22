import os
from logging.config import fileConfig
from typing import Final

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context
from src.database.models._base import _Base

# Load .env file
load_dotenv()


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
target_metadata = _Base.metadata

# other values from the config, defined by the needs of env.py,
DECLARED_SCHEMATA: Final = ["user_data", "knowledge"]


def include_name(name, type_, _parent_names) -> bool:
    """Configure the schema names to be included in the autogeneration."""
    if type_ == "schema":
        print(f"Schema: {name}")
        return name in DECLARED_SCHEMATA
    return True


# Alembic context settings
CTX_SETTINGS: Final = {
    "target_metadata": target_metadata,
    "include_schemas": True,
    "include_name": include_name,
    "dialect_opts": {"paramstyle": "named"},
}


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    # Load the connection string from the .env variable
    if "LOG_CHAT_DB" in os.environ:
        db_url = os.getenv("LOG_CHAT_DB")
        config.set_main_option("sqlalchemy.url", db_url)  # type: ignore

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        ctx_settings = CTX_SETTINGS | {"connection": connection}
        context.configure(**ctx_settings)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise NotImplementedError("Offline mode is not supported.")
else:
    run_migrations_online()
