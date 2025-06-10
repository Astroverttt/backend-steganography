from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings # Mengimpor objek settings
from sqlalchemy.orm import Session
import os

from dotenv import load_dotenv
load_dotenv()

# --- BARIS INI YANG HARUS DIPERBAIKI ---
# Mengambil URL database dari objek settings.
# Pastikan di file .env Anda, variabelnya bernama DATABASE_URL
# dan di app/core/config.py, properti di kelas Settings juga bernama DATABASE_URL.
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Baris ini tidak diperlukan karena SQLALCHEMY_DATABASE_URL sudah didefinisikan di atas
# DBURL = settings.DBURL

# Menggunakan URL database yang sudah benar untuk membuat engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()