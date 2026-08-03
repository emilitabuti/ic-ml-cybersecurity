"""Configuração única do pipeline temporal UNSW-NB15."""
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False


load_dotenv()

RANDOM_SEED: int = 42
WINDOW_SIZE: int = 10
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.8"))
MODEL_ARTIFACT_PATH: str = os.getenv(
    "MODEL_ARTIFACT_PATH",
    "models/model_rf_temporal_v2.pkl",
)

FEATURE_SELECTION_TOP_N: int = 30
FEATURE_SELECTION_THRESHOLD: float = 0.0
FEATURE_SELECTION_ARTIFACT_PATH: str = os.getenv(
    "FEATURE_SELECTION_ARTIFACT_PATH",
    "reports_temporal/unsw/final_evaluation/feature_ranking_train_validation.json",
)

RF_N_ESTIMATORS: int = 100
RF_MAX_DEPTH: str | None = "20"
DT_MAX_DEPTH: str | None = "20"
RF_N_JOBS: int = 2
LSTM_EPOCHS: int = 10
LSTM_BATCH_SIZE: int = 4096
