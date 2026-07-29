from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes.predict import router as predict_router
from src.api.services import prediction_service
from src.api.services.prediction_service import (
    InvalidFeaturesError,
    ModelNotLoadedError,
    PredictionError,
    load_model_once,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model_once()
    yield


app = FastAPI(
    title="IC ML Cybersecurity API",
    description="API de inferência para detecção de intrusões com ML.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(predict_router)


@app.exception_handler(InvalidFeaturesError)
async def invalid_features_handler(_, exc: InvalidFeaturesError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "code": exc.code},
    )


@app.exception_handler(ModelNotLoadedError)
async def model_not_loaded_handler(_, exc: ModelNotLoadedError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "code": exc.code},
    )


@app.exception_handler(PredictionError)
async def prediction_error_handler(_, exc: PredictionError) -> JSONResponse:
    logger.error("Erro de predição: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "code": exc.code},
    )


@app.get("/health", tags=["infra"])
def health_check() -> dict:
    health = {"status": "ok", "version": app.version, "model": None}
    try:
        health["model"] = prediction_service.model_info()["model_type"]
    except ModelNotLoadedError:
        logger.warning("Health check executado antes do modelo estar carregado.")
    return health
