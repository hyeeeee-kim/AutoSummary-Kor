"""Global configuration - loads all settings from environment variables"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Disable Chroma telemetry before importing chromadb modules
os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "output"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# LLM Configuration (Ollama with Mistral 7B)
# Mistral 7B is recommended for RAG systems:
# - Better context understanding (8K tokens)
# - Faster inference than Llama 2 13B
# - Superior instruction following for summarization
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral")
LLM_MAX_TOKENS = 800

# Embedding Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "UAE-Large-V1")
EMBEDDING_BATCH_SIZE = 32

# Vector Database (Chroma)
CHROMA_PATH = DATA_DIR / "chroma"
CHROMA_PATH.mkdir(exist_ok=True)
CHROMA_TELEMETRY_DISABLED = os.getenv("CHROMA_TELEMETRY_DISABLED", "True") == "True"

# Search Configuration
DENSE_TOP_K = 50
SPARSE_WEIGHT = 0.3
DENSE_WEIGHT = 0.7

# Web Scraping Configuration
SCRAPER_TIMEOUT = 20
SCRAPER_RETRIES = 2
NUM_WORKERS = 16
ABSTRACT_WORKERS = 10

