import os
from fastapi import FastAPI
from app.db.database import Base, engine
from app.api.routes import users, auth, uploads, explore, payments
from dotenv import load_dotenv

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(uploads.router, prefix="/api/artwork", tags=["Artworks"])
app.include_router(explore.router, prefix="/explores", tags=["Explores"])
app.include_router(payments.router, prefix="/payments", tags=["Payments"])
