import os
import logging
from fastapi import FastAPI
from dotenv import load_dotenv
from app.db.database import Base, engine
from app.api.routes import users, auth, uploads, explore, payments

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI()

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "app.log")),
        logging.StreamHandler() 
    ]
)

logger = logging.getLogger(__name__)
logger.info("Server FastAPI dimulai...")

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(uploads.router, prefix="/api/artwork", tags=["Artworks"])
app.include_router(explore.router, prefix="/explores", tags=["Explores"])
app.include_router(payments.router, prefix="/payments", tags=["Payments"])
