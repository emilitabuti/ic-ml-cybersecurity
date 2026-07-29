from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    prediction: str = Field(..., description="Tipo de ameaça ou tráfego previsto.")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confiança da predição, entre 0.0 e 1.0.",
    )
    model: str = Field(..., description="Identificador do modelo que gerou a predição.")
    timestamp: str = Field(..., description="Timestamp da predição em ISO 8601 UTC.")
    source_prediction: str | None = Field(
        None,
        description="Rotulo original do cenario/evento usado para filtros do dashboard.",
    )


class PredictionHistoryItem(PredictionResponse):
    pass


class ModelInfoResponse(BaseModel):
    model_type: str = Field(..., description="Tipo de algoritmo carregado.")
    window_size: int = Field(..., description="Tamanho da janela usado no treino.")
    features: list[str] = Field(..., description="Features esperadas pelo modelo.")
    trained_at: str | None = Field(
        None,
        description="Data de treino/criação do artefato.",
    )
