from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings # Mengimpor objek settings
from sqlalchemy.orm import Session
import os

from dotenv import load_dotenv
load_dotenv()

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

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