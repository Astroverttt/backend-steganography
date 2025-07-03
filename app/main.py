import os
import logging
from fastapi import FastAPI
from fastapi import staticfiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.db.database import Base, engine
from app.api.routes import users, auth, uploads, explore, payments, extract, likes


load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", staticfiles.StaticFiles(directory="static"), name="static")

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
    allow_origins=["*"],          
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(uploads.router, prefix="/api/artwork", tags=["Artworks"])
app.include_router(explore.router, prefix="/explores", tags=["Explores"])
app.include_router(payments.router, prefix="/payments", tags=["Payments"])
app.include_router(extract.router, prefix="/extract", tags=["Extract"])
app.include_router(likes.router, prefix="/likes", tags=["Likes"])
