import os
import sys
from pathlib import Path


os.environ.setdefault("CHGKA_ENV", "development")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")
os.environ.setdefault("ADMIN_TOKEN_TTL_SECONDS", "43200")
os.environ.setdefault("CHGKA_DB_PATH", ":memory:")

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
