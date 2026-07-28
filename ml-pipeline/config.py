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

K_FOLDS: int = int(os.getenv("K_FOLDS", "5"))
MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "mlruns")
TRAINING_REPORTS_DIR: str = os.getenv("TRAINING_REPORTS_DIR", "reports")

RF_N_ESTIMATORS: int = int(os.getenv("RF_N_ESTIMATORS", "100"))
# max_depth limitado (em vez de None/ilimitado): com WINDOW_SIZE=10, o numero de
# colunas efetivo (features x janela) fica alto o suficiente para deixar arvores
# sem limite de profundidade impraticaveis em datasets grandes (ex.: UNSW-NB15,
# 206 features x 10 = 2060 colunas, 1.58M linhas). 20 e um valor comum na
# literatura para RF/DT em deteccao de intrusao e mantem o treino viavel.
RF_MAX_DEPTH: str | None = os.getenv("RF_MAX_DEPTH", "20") or None
DT_MAX_DEPTH: str | None = os.getenv("DT_MAX_DEPTH", "20") or None
# n_jobs alto multiplica o overhead de memoria de construcao de arvore (buffers
# internos de ordenacao por thread) pelo numero de threads concorrentes. Em
# datasets largos (UNSW-NB15, 2060 colunas) isso pode dobrar/triplicar o pico de
# RAM e causar OOM-kill silencioso. Valor baixo por padrao prioriza estabilidade
# sobre velocidade; pode ser ajustado via env var quando a RAM disponivel permitir.
RF_N_JOBS: int = int(os.getenv("RF_N_JOBS", "2"))
MLP_HIDDEN_LAYER_SIZES: str = os.getenv("MLP_HIDDEN_LAYER_SIZES", "64,32")
MLP_MAX_ITER: int = int(os.getenv("MLP_MAX_ITER", "200"))
LSTM_EPOCHS: int = int(os.getenv("LSTM_EPOCHS", "10"))
LSTM_BATCH_SIZE: int = int(os.getenv("LSTM_BATCH_SIZE", "256"))
