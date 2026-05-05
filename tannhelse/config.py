import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs" / "corpus"
DB_PATH = ROOT / "store.db"
DOCS_YAML = ROOT / "docs" / "docs.yaml"

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
LLM_MODEL = "deepseek-chat"

CHUNK_SIZE_TOKENS = 600
CHUNK_MAX_TOKENS = 900
CHUNK_OVERLAP_TOKENS = 100
TOP_K_GLOBAL = 15
TOP_K_PER_DOC = 8

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
