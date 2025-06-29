import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy import pool
from alembic import context
from app.db.database import Base

target_metadata = Base.metadata

# Tambahkan path ke root proyek Anda agar model dapat diimpor
# Ini sangat penting agar Python bisa menemukan modul 'app.db.database' dan 'app.models'
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# --- START DEBUGGING IMPORTS ---
print(f"DEBUG: sys.path after append: {sys.path}")
print(f"DEBUG: Project root added: {project_root}")

try:
    # Import Base SQLAlchemy Anda dan semua model Anda
    from app.db.database import Base
    print("DEBUG: Successfully imported app.db.database.Base")

    # Penting: Impor SEMUA model yang ingin Anda lacak dengan Alembic
    from app.models.artwork import Artwork
    from app.models.user import User
    # from app.models.receipt import Receipt
    # from app.models.your_other_model import YourOtherModel # Jika ada model lain
    print("DEBUG: Successfully imported all models (Artwork, User, Receipt)")

    # Target MetaData untuk autogenerate support
    target_metadata = Base.metadata
    if target_metadata is None:
        print("DEBUG: Base.metadata is None. This is a problem.")
    elif not target_metadata.tables:
        print("DEBUG: Base.metadata is not empty, but contains no tables. Check model definitions.")
    else:
        print(f"DEBUG: Base.metadata contains {len(target_metadata.tables)} tables.")
        for table_name in target_metadata.tables:
            print(f"  - {table_name}")

except ImportError as e:
    print(f"ERROR: Failed to import modules. Check sys.path and module paths: {e}")
    sys.exit(1) # Keluar jika import gagal
except Exception as e:
    print(f"ERROR: An unexpected error occurred during import: {e}")
    sys.exit(1)
# --- END DEBUGGING IMPORTS ---

# Ini adalah objek Alembic Config
config = context.config

# Konfigurasi logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ... (sisa kode env.py tetap sama) ...

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
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
        future=True, # Penting untuk SQLAlchemy 1.4+
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, future=True
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

