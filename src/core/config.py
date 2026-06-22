import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/app.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MOODLE_BASE_URL = os.getenv("MOODLE_BASE_URL", "http://localhost:8080").rstrip("/")
MOODLE_TOKEN = os.getenv("MOODLE_TOKEN", "")

DISCIPLINES = {
    "Programação (Python)": "python",
    "Estruturas de Dados": "ds",
    "Banco de Dados (SQL)": "sql",
}
