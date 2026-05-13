from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
import models  # noqa

from auth import router as auth_router
from tweets import router as tweets_router
from follows import router as follows_router
from notifications import router as notifications_router
from websocket import router as websocket_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nexus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tweets_router)
app.include_router(follows_router)
app.include_router(notifications_router)
app.include_router(websocket_router)

@app.get("/")
def root():
    return {"message": "Nexus API is running"}