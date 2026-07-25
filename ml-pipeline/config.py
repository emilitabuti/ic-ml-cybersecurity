import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False

load_dotenv()

RANDOM_SEED: int = 42
TEST_SIZE: float = float(os.getenv("TEST_SIZE", "0.2"))
WINDOW_SIZE: int = int(os.getenv("WINDOW_SIZE", "10"))
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.8"))
MODEL_PATH: str = os.getenv("MODEL_PATH", "models/")
FEATURE_SELECTION_TOP_N: int = int(os.getenv("FEATURE_SELECTION_TOP_N", "20"))
FEATURE_SELECTION_THRESHOLD: float = float(os.getenv("FEATURE_SELECTION_THRESHOLD", "0.0"))
FEATURE_SELECTION_ARTIFACT_PATH: str = os.getenv(
    "FEATURE_SELECTION_ARTIFACT_PATH",
    "models/feature_selection.json",
)
