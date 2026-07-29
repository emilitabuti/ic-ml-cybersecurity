from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.predict import router as predict_router

app = FastAPI(
    title="IC ML Cybersecurity API",
    description="API de inferência para detecção de intrusões com ML.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(predict_router)


@app.get("/health", tags=["infra"])
def health_check() -> dict:
    return {"status": "ok", "version": app.version}
