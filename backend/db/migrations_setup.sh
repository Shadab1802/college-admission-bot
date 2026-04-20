# Alembic Migration Setup
# Run these commands ONCE from inside /backend after activating venv

# 1. Initialize alembic
alembic init db/migrations

# 2. In db/migrations/env.py, replace the target_metadata line:
#    from models.db_models import Base
#    target_metadata = Base.metadata

# 3. In alembic.ini, set:
#    sqlalchemy.url = (leave blank — we override in env.py)

# 4. In db/migrations/env.py, add this to load from .env:
#    from dotenv import load_dotenv
#    import os
#    load_dotenv()
#    config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# 5. Create your first migration:
alembic revision --autogenerate -m "initial schema"

# 6. Apply it to Supabase:
alembic upgrade head

# ── After any model change ──────────────────────────────────
alembic revision --autogenerate -m "describe your change"
alembic upgrade head