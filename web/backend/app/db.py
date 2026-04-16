from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()


DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "cocktail_database.db"
DB_PATH = Path(os.getenv("COCKTAIL_DB_PATH", str(DEFAULT_DB_PATH))).resolve()


@contextmanager
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
