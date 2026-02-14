from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "historic.db"

# LLM
LLM_BASE_URL = "http://localhost:8080/v1"
LLM_MODEL_NAME = "ministral"

# Server
API_HOST = "127.0.0.1"
API_PORT = 8081
CORS_ORIGINS = ["http://localhost:5173"]
