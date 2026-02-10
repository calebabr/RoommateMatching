from fastapi import FastAPI
from app.routers import matchRoutes

app = FastAPI(
    title="Matching Algorithm",
    description = "Simple matching algorithm based on numerical rateable category preferences",
    version="0.1.0",
)

app.include_router(matchRoutes.router)

@app.get("/")
def root():
    return {"status": "Matching Algorithm API running", "version": "0.1.0"}

@app.get("/health")
def health():
    return {"status": "ok"}