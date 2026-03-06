import os
from dotenv import load_dotenv

load_dotenv()

RANDOM_SEED: int = 42
TEST_SIZE: float = float(os.getenv("TEST_SIZE", "0.2"))
WINDOW_SIZE: int = int(os.getenv("WINDOW_SIZE", "10"))
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.8"))
MODEL_PATH: str = os.getenv("MODEL_PATH", "models/")
