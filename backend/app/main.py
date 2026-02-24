from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import matchRoutes
from app.routers.matchingRoutes import router as matchingRouter
from app.routers.userRoutes import router as userRouter

app = FastAPI(
    title="Matching Algorithm",
    description = "Simple matching algorithm based on numerical rateable category preferences",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matchingRouter, prefix="/api")
app.include_router(userRouter, prefix="/api")

@app.get("/")
def root():
    return {"status": "Matching Algorithm API running", "version": "0.1.0"}

@app.get("/health")
def health():
    return {"status": "ok"}