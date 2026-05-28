import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers.matchingRoutes import router as matchingRouter
from app.routers.userRoutes import router as userRouter
from app.routers.authRoutes import router as authRouter
from app.database import users_collection

@asynccontextmanager
async def lifespan(app: FastAPI):
    await users_collection.create_index("email", unique=True, sparse=True)
    yield

app = FastAPI(title="RoomMatch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded photos as static files at /uploads/filename.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(authRouter, prefix="/api")
app.include_router(matchingRouter, prefix="/api")
app.include_router(userRouter, prefix="/api")

@app.get("/")
def root():
    return {"status": "Matching Algorithm API running", "version": "0.2.0"}

@app.get("/health")
def health():
    return {"status": "ok"}