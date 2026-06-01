from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import cv, ml, iot, dashboard

app = FastAPI(
    title="API",
    description="Plataforma de inteligência ambiental e agrícola com dados de satélite e IA.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cv.router, prefix="/cv", tags=["Computer Vision"])
app.include_router(ml.router, prefix="/ml", tags=["Machine Learning"])
app.include_router(iot.router, prefix="/iot", tags=["IoT"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
