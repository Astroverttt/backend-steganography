import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.db.database import Base, engine
from app.api.routes import users, auth, uploads, explore, payments, extract, likes 

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

origins = [
    "http://localhost:3000",
    "http://192.168.56.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.56.1:3000"
    ],  # <- sesuaikan jika nanti deploy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(uploads.router, prefix="/api/artwork", tags=["Artworks"])
app.include_router(explore.router, prefix="/api/explores", tags=["Explores"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(extract.router, prefix="/api/extract", tags=["Extract"])
app.include_router(likes.router, prefix="/api/likes", tags=["Likes"])
app.mount("/api/static", StaticFiles(directory="static"), name="static")
