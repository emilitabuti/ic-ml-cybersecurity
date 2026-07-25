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
