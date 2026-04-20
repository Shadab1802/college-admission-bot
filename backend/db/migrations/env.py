from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv
from pathlib import Path
import os
import sys
 
# ── Make sure backend/ is on the path ─────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
 
# ── Load .env for local dev ───────────────────────────────
load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / "backend" / ".env")
 
# ── Import all models so Alembic sees them ────────────────
from models.db_models import Base   # noqa: E402
 
config = context.config
 
# ── Inject DATABASE_URL from environment ──────────────────
# Works both locally (from .env) and on Render (from dashboard env vars)
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL not set. Check your .env or Render environment variables.")
config.set_main_option("sqlalchemy.url", database_url)
 
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
 
target_metadata = Base.metadata
 
 
def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
 
 
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()