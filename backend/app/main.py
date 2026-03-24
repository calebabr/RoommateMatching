import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers.matchingRoutes import router as matchingRouter
from app.routers.userRoutes import router as userRouter
from app.routers.chatRoutes import router as chatRouter
from app.services.chatService import ChatService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create indexes
    chat = ChatService()
    await chat.ensure_indexes()
    yield
    # Shutdown: nothing needed


app = FastAPI(title="RoomMatch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "photos")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "uploads")), name="uploads")

app.include_router(matchingRouter, prefix="/api")
app.include_router(userRouter, prefix="/api")
app.include_router(chatRouter, prefix="/api")

@app.get("/")
def root():
    return {"status": "Matching Algorithm API running", "version": "0.3.0"}

@app.get("/health")
def health():
    return {"status": "ok"}