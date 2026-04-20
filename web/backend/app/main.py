from __future__ import annotations

import json
import logging
import os
import re
import uuid
import base64
import binascii
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import quote, urlparse

import requests
import psycopg
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row

from .db import DB_PATH, get_connection
from .schemas import (
    AlcoholWriteRequest,
    CocktailWriteRequest,
    CountsResponse,
    HealthResponse,
    SavedViewCreateRequest,
    SavedViewItem,
    SavedViewListResponse,
    TagCreateRequest,
    TagItem,
    TagListResponse,
    TastingLogCreateRequest,
    TastingLogItem,
    TastingLogListResponse,
    TwistRequest,
    TwistResponse,
    TwistSuggestion,
)


app = FastAPI(title="Cocktail Database API", version="0.1.0")
logger = logging.getLogger(__name__)

if getattr(sys, "frozen", False):
    INSTALL_ROOT = Path(sys.executable).resolve().parents[2]
    REPO_ROOT = INSTALL_ROOT
    BACKEND_ROOT = (INSTALL_ROOT / "web" / "backend").resolve()
else:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE_PATH = BACKEND_ROOT / ".env"
LOCAL_DB_PATH = (REPO_ROOT / "cocktail_database.db").resolve()
LOCAL_IMAGES_DIR = (REPO_ROOT / "images").resolve()
LAST_MIRROR_SYNC_AT = ""
DEFAULT_IMAGES_DIR = REPO_ROOT / "images"
_images_path_env = str(os.getenv("COCKTAIL_IMAGES_PATH", "")).strip()
if _images_path_env:
    _images_candidate = Path(_images_path_env)
    if not _images_candidate.is_absolute():
        _images_candidate = REPO_ROOT / _images_candidate
    IMAGES_DIR = _images_candidate.resolve()
else:
    IMAGES_DIR = DEFAULT_IMAGES_DIR.resolve()
FLAGS_DIR = IMAGES_DIR / "flags"
app.mount("/images", StaticFiles(directory=str(IMAGES_DIR), check_dir=False), name="images")
FRONTEND_DIST_DIR = (BACKEND_ROOT.parent / "frontend" / "dist").resolve()
app.mount("/assets", StaticFiles(directory=str((FRONTEND_DIST_DIR / "assets").resolve()), check_dir=False), name="frontend-assets")

ALLOWED_UPLOAD_CATEGORIES = {
    "liquors": IMAGES_DIR / "liquors",
    "cocktails": IMAGES_DIR / "cocktails",
}

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
WIKIMEDIA_ALLOWED_HOST_SUFFIXES = ("wikimedia.org", "wikipedia.org")
WIKIMEDIA_HEADERS = {
    "User-Agent": "CocktailDatabase/1.0 (Wikimedia image fetch feature)",
}
WEB_LOOKUP_HEADERS = {
    "User-Agent": "CocktailDatabase/1.0 (Web hints lookup)",
}


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


STORAGE_MODE = str(os.getenv("STORAGE_MODE", "supabase")).strip().lower() or "supabase"
LOCAL_MIRROR_ENABLED = _parse_bool_env("LOCAL_MIRROR_ENABLED", True)
LOCAL_MIRROR_BEST_EFFORT = _parse_bool_env("LOCAL_MIRROR_BEST_EFFORT", True)
SUPABASE_URL = str(os.getenv("SUPABASE_URL", "")).strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
SUPABASE_DB_URL = str(os.getenv("SUPABASE_DB_URL", "")).strip()
SUPABASE_STORAGE_BUCKET = str(os.getenv("SUPABASE_STORAGE_BUCKET", "images")).strip() or "images"
USE_SUPABASE = bool(
    STORAGE_MODE == "supabase"
    and SUPABASE_URL
    and SUPABASE_SERVICE_ROLE_KEY
    and SUPABASE_DB_URL
)

COUNTRY_TO_ISO2_OVERRIDES = {
    "usa": "us",
    "u s a": "us",
    "us": "us",
    "u s": "us",
    "united states": "us",
    "united states of america": "us",
    "uk": "gb",
    "u k": "gb",
    "great britain": "gb",
    "england": "gb",
    "scotland": "gb",
    "wales": "gb",
    "northern ireland": "gb",
    "new zealand": "nz",
    "south korea": "kr",
    "north korea": "kp",
    "czech republic": "cz",
    "czechia": "cz",
    "russia": "ru",
    "vietnam": "vn",
    "uae": "ae",
    "u a e": "ae",
    "united arab emirates": "ae",
}

TASTING_EXTRA_COLUMNS = [
    ("mood", "TEXT"),
    ("occasion", "TEXT"),
    ("location", "TEXT"),
    ("would_make_again", "TEXT"),
    ("change_next_time", "TEXT"),
    ("sweetness", "TEXT"),
    ("sourness", "TEXT"),
    ("bitterness", "TEXT"),
    ("booziness", "TEXT"),
    ("body", "TEXT"),
    ("aroma", "TEXT"),
    ("balance", "TEXT"),
    ("finish", "TEXT"),
]

ALCOHOL_COLUMNS = [
    "Brand", "Base_Liquor", "Type", "ABV", "Country",
    "Price_NZD_700ml", "Taste", "Substitute", "Availability", "image_path",
]

COCKTAIL_COLUMNS = [
    "Cocktail_Name", "Ingredients", "Rating_Jason", "Rating_Jaime", "Rating_overall",
    "Base_spirit_1", "Type1", "Brand1", "Base_spirit_2", "Type2", "Brand2",
    "Citrus", "Garnish", "Notes", "DatetimeAdded", "Prep_Time", "Difficulty", "image_path",
]

TASTING_COLUMNS = [
    "id", "date", "cocktail_name", "rating", "notes", "mood", "occasion", "location",
    "would_make_again", "change_next_time", "sweetness", "sourness", "bitterness",
    "booziness", "body", "aroma", "balance", "finish", "created_at",
]

TAG_COLUMNS = ["id", "entity_type", "entity_rowid", "tag", "created_at"]
SAVED_VIEW_COLUMNS = ["id", "name", "payload_json", "created_at"]


def _quote_pg(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'


def _pg_columns(columns: List[str]) -> str:
    return ", ".join(_quote_pg(col) for col in columns)


@contextmanager
def _get_supabase_connection():
    if not USE_SUPABASE:
        raise HTTPException(status_code=500, detail="Supabase mode is not configured")
    conn = psycopg.connect(SUPABASE_DB_URL, prepare_threshold=None, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def _pg_fetch_all(query: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    with _get_supabase_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    return [dict(row) for row in rows]


def _pg_fetch_one(query: str, params: Tuple[Any, ...] = ()) -> Dict[str, Any] | None:
    with _get_supabase_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
    return dict(row) if row else None


def _pg_execute(query: str, params: Tuple[Any, ...] = ()) -> int:
    with _get_supabase_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rowcount = cur.rowcount or 0
        conn.commit()
    return rowcount


def _next_pg_id(table_name: str) -> int:
    row = _pg_fetch_one(f"SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM {table_name}")
    return int(row["next_id"]) if row else 1


def _normalize_image_key(path_value: str) -> str:
    raw = str(path_value or "").strip()
    if not raw:
        return ""

    public_prefix = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/"
    if SUPABASE_URL and raw.startswith(public_prefix):
        raw = raw[len(public_prefix):]

    raw = raw.split("?", 1)[0].replace("\\", "/")
    while raw.startswith("./"):
        raw = raw[2:]
    if raw.lower().startswith("images/"):
        raw = raw[7:]
    return raw.strip("/")


def _to_local_image_path(path_value: str) -> str:
    key = _normalize_image_key(path_value)
    if not key:
        return ""
    if key.startswith("http://") or key.startswith("https://") or key.startswith("data:"):
        return key
    return f"images/{key}"


def _resolve_image_path_for_response(path_value: str) -> str:
    raw = str(path_value or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://") or raw.startswith("data:"):
        return raw
    if USE_SUPABASE:
        key = _normalize_image_key(raw)
        if key:
            return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{key}"
    return raw


def _resolve_image_paths_in_row(row: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(row)
    if "image_path" in item:
        item["image_path"] = _resolve_image_path_for_response(str(item.get("image_path") or ""))
    return item


def _mirror_local(task_name: str, fn) -> None:
    if not LOCAL_MIRROR_ENABLED:
        return
    try:
        fn()
    except Exception as exc:
        if LOCAL_MIRROR_BEST_EFFORT:
            logger.warning("Local mirror failed for %s: %s", task_name, exc)
            return
        raise HTTPException(status_code=500, detail=f"Local mirror failed for {task_name}: {exc}") from exc


def _assert_storage_controls_available() -> None:
    if USE_SUPABASE and not LOCAL_MIRROR_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="Local storage controls are disabled in cloud-only mode. Enable LOCAL_MIRROR_ENABLED to use this endpoint.",
        )


def _mirror_upsert_alcohol_by_brand(previous_brand: str, data: Dict[str, Any]) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        local_image_path = _to_local_image_path(data.get("image_path", ""))
        lookup_brand = previous_brand.strip() if previous_brand.strip() else str(data.get("Brand") or "").strip()

        cur.execute(
            """
            UPDATE alcohol_inventory
            SET Brand = ?, Base_Liquor = ?, Type = ?, ABV = ?, Country = ?,
                Price_NZD_700ml = ?, Taste = ?, Substitute = ?, Availability = ?, image_path = ?
            WHERE rowid = (
                SELECT rowid FROM alcohol_inventory WHERE Brand = ? LIMIT 1
            )
            """,
            (
                data["Brand"],
                data["Base_Liquor"],
                data["Type"],
                data["ABV"],
                data["Country"],
                data["Price_NZD_700ml"],
                data["Taste"],
                data["Substitute"],
                data["Availability"],
                local_image_path,
                lookup_brand,
            ),
        )

        if cur.rowcount == 0:
            cur.execute(
                """
                INSERT INTO alcohol_inventory (
                    Brand, Base_Liquor, Type, ABV, Country,
                    Price_NZD_700ml, Taste, Substitute, Availability, image_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["Brand"],
                    data["Base_Liquor"],
                    data["Type"],
                    data["ABV"],
                    data["Country"],
                    data["Price_NZD_700ml"],
                    data["Taste"],
                    data["Substitute"],
                    data["Availability"],
                    local_image_path,
                ),
            )

        conn.commit()


def _mirror_delete_alcohol_by_brand(brand: str) -> None:
    if not str(brand or "").strip():
        return
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM alcohol_inventory
            WHERE rowid = (
                SELECT rowid FROM alcohol_inventory WHERE Brand = ? LIMIT 1
            )
            """,
            (brand.strip(),),
        )
        conn.commit()


def _mirror_upsert_cocktail_by_name(previous_name: str, data: Dict[str, Any]) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        local_image_path = _to_local_image_path(data.get("image_path", ""))
        lookup_name = previous_name.strip() if previous_name.strip() else str(data.get("Cocktail_Name") or "").strip()

        cur.execute(
            """
            UPDATE cocktail_notes
            SET Cocktail_Name = ?, Ingredients = ?, Rating_Jason = ?, Rating_Jaime = ?, Rating_overall = ?,
                Base_spirit_1 = ?, Type1 = ?, Brand1 = ?, Base_spirit_2 = ?, Type2 = ?, Brand2 = ?,
                Citrus = ?, Garnish = ?, Notes = ?, DatetimeAdded = ?, Prep_Time = ?, Difficulty = ?, image_path = ?
            WHERE rowid = (
                SELECT rowid FROM cocktail_notes WHERE Cocktail_Name = ? LIMIT 1
            )
            """,
            (
                data["Cocktail_Name"],
                data["Ingredients"],
                data["Rating_Jason"],
                data["Rating_Jaime"],
                data["Rating_overall"],
                data["Base_spirit_1"],
                data["Type1"],
                data["Brand1"],
                data["Base_spirit_2"],
                data["Type2"],
                data["Brand2"],
                data["Citrus"],
                data["Garnish"],
                data["Notes"],
                data["DatetimeAdded"],
                data["Prep_Time"],
                data["Difficulty"],
                local_image_path,
                lookup_name,
            ),
        )

        if cur.rowcount == 0:
            cur.execute(
                """
                INSERT INTO cocktail_notes (
                    Cocktail_Name, Ingredients, Rating_Jason, Rating_Jaime, Rating_overall,
                    Base_spirit_1, Type1, Brand1, Base_spirit_2, Type2, Brand2,
                    Citrus, Garnish, Notes, DatetimeAdded, Prep_Time, Difficulty, image_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["Cocktail_Name"],
                    data["Ingredients"],
                    data["Rating_Jason"],
                    data["Rating_Jaime"],
                    data["Rating_overall"],
                    data["Base_spirit_1"],
                    data["Type1"],
                    data["Brand1"],
                    data["Base_spirit_2"],
                    data["Type2"],
                    data["Brand2"],
                    data["Citrus"],
                    data["Garnish"],
                    data["Notes"],
                    data["DatetimeAdded"],
                    data["Prep_Time"],
                    data["Difficulty"],
                    local_image_path,
                ),
            )

        conn.commit()


def _mirror_delete_cocktail_by_name(cocktail_name: str) -> None:
    if not str(cocktail_name or "").strip():
        return
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM cocktail_notes
            WHERE rowid = (
                SELECT rowid FROM cocktail_notes WHERE Cocktail_Name = ? LIMIT 1
            )
            """,
            (cocktail_name.strip(),),
        )
        conn.commit()


def _upload_to_supabase_storage(key: str, content: bytes, content_type: str) -> None:
    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{key}"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": content_type or "application/octet-stream",
        "x-upsert": "true",
    }
    response = requests.post(url, headers=headers, data=content, timeout=60)
    if not response.ok:
        raise HTTPException(status_code=502, detail=f"Supabase storage upload failed: {response.text[:300]}")


@app.on_event("startup")
def ensure_tasting_log_table() -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasting_log (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                cocktail_name TEXT NOT NULL,
                rating TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_views (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_rowid INTEGER NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        existing_columns = {row[1] for row in cur.execute("PRAGMA table_info(tasting_log)").fetchall()}
        for column_name, column_type in TASTING_EXTRA_COLUMNS:
            if column_name not in existing_columns:
                cur.execute(f"ALTER TABLE tasting_log ADD COLUMN {column_name} {column_type}")
        conn.commit()


def _ensure_core_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS alcohol_inventory (
            Brand TEXT,
            Base_Liquor TEXT,
            Type TEXT,
            ABV TEXT,
            Country TEXT,
            Price_NZD_700ml TEXT,
            Taste TEXT,
            Substitute TEXT,
            Availability TEXT,
            image_path TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cocktail_notes (
            Cocktail_Name TEXT,
            Ingredients TEXT,
            Rating_Jason TEXT,
            Rating_Jaime TEXT,
            Rating_overall TEXT,
            Base_spirit_1 TEXT,
            Type1 TEXT,
            Brand1 TEXT,
            Base_spirit_2 TEXT,
            Type2 TEXT,
            Brand2 TEXT,
            Citrus TEXT,
            Garnish TEXT,
            Notes TEXT,
            DatetimeAdded TEXT,
            Prep_Time TEXT,
            Difficulty TEXT,
            image_path TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasting_log (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            cocktail_name TEXT NOT NULL,
            rating TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_views (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_rowid INTEGER NOT NULL,
            tag TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    existing_columns = {row[1] for row in cur.execute("PRAGMA table_info(tasting_log)").fetchall()}
    for column_name, column_type in TASTING_EXTRA_COLUMNS:
        if column_name not in existing_columns:
            cur.execute(f"ALTER TABLE tasting_log ADD COLUMN {column_name} {column_type}")

    conn.commit()


def _storage_root_from_paths(db_path: Path, images_path: Path) -> Path:
    if images_path.parent == db_path.parent:
        return db_path.parent
    return db_path.parent


def _path_last_modified_iso(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
    except OSError:
        return ""


def _now_local_iso(timespec: str = "seconds") -> str:
    return datetime.now().astimezone().isoformat(timespec=timespec)


def _resolve_target_paths(root_path: str) -> Tuple[Path, Path, Path]:
    if not str(root_path or "").strip():
        raise HTTPException(status_code=400, detail="root_path is required")

    root = Path(str(root_path).strip())
    if not root.is_absolute():
        root = (REPO_ROOT / root).resolve()
    else:
        root = root.resolve()

    db_path = root / "cocktail_database.db"
    images_path = root / "images"
    return root, db_path, images_path


def _assert_directory_writable(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Selected folder does not exist: {path}")

    probe_path = path / f".write-probe-{uuid.uuid4().hex}.tmp"
    try:
        probe_path.write_text("ok", encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Selected folder is not writable: {path}") from exc
    finally:
        try:
            if probe_path.exists():
                probe_path.unlink()
        except OSError:
            pass


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def _safe_table_count(conn: sqlite3.Connection, table_name: str) -> int:
    if not _table_exists(conn, table_name):
        return 0
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    row = cur.fetchone()
    return int(row[0]) if row else 0


def _safe_latest_value(conn: sqlite3.Connection, table_name: str, column_name: str) -> str:
    if not _table_exists(conn, table_name):
        return ""

    column_names = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in column_names:
        return ""

    cur = conn.cursor()
    cur.execute(
        f"SELECT COALESCE(MAX({column_name}), '') FROM {table_name}"
    )
    row = cur.fetchone()
    return str(row[0] or "").strip() if row else ""


def _collect_db_stats(db_path: Path) -> Dict[str, Any]:
    if not db_path.exists() or not db_path.is_file():
        return {
            "exists": False,
            "path": str(db_path),
            "counts": {
                "alcohol_inventory": 0,
                "cocktail_notes": 0,
                "tasting_log": 0,
                "saved_views": 0,
                "tags": 0,
            },
            "latest": {
                "cocktail_notes": "",
                "tasting_log": "",
                "saved_views": "",
                "tags": "",
            },
        }

    conn = sqlite3.connect(db_path)
    try:
        counts = {
            "alcohol_inventory": _safe_table_count(conn, "alcohol_inventory"),
            "cocktail_notes": _safe_table_count(conn, "cocktail_notes"),
            "tasting_log": _safe_table_count(conn, "tasting_log"),
            "saved_views": _safe_table_count(conn, "saved_views"),
            "tags": _safe_table_count(conn, "tags"),
        }
        latest = {
            "cocktail_notes": _safe_latest_value(conn, "cocktail_notes", "DatetimeAdded"),
            "tasting_log": _safe_latest_value(conn, "tasting_log", "created_at"),
            "saved_views": _safe_latest_value(conn, "saved_views", "created_at"),
            "tags": _safe_latest_value(conn, "tags", "created_at"),
        }
        return {
            "exists": True,
            "path": str(db_path),
            "counts": counts,
            "latest": latest,
        }
    finally:
        conn.close()


def _is_empty_location(db_path: Path, images_path: Path) -> bool:
    return (not db_path.exists()) and (not images_path.exists())


def _backup_file(src_path: Path, backup_dir: Path, label: str) -> str:
    if not src_path.exists() or not src_path.is_file():
        return ""
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_path = backup_dir / f"{label}-{stamp}{src_path.suffix or '.bak'}"
    shutil.copy2(src_path, target_path)
    return str(target_path)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    return bool(str(value).strip())


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            return parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _is_source_newer(source_row: Dict[str, Any], target_row: Dict[str, Any], datetime_fields: List[str]) -> bool | None:
    for field in datetime_fields:
        source_dt = _parse_dt(source_row.get(field))
        target_dt = _parse_dt(target_row.get(field))
        if source_dt and target_dt:
            if source_dt > target_dt:
                return True
            if source_dt < target_dt:
                return False
        elif source_dt and not target_dt:
            return True
        elif target_dt and not source_dt:
            return False
    return None


def _merge_field_value(source_value: Any, target_value: Any, source_newer: bool | None) -> Any:
    if source_newer is True:
        return source_value if _has_value(source_value) else target_value
    if source_newer is False:
        return target_value if _has_value(target_value) else source_value
    return target_value if _has_value(target_value) else source_value


def _merge_by_normalized_key(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    table_name: str,
    columns: List[str],
    key_builder,
    datetime_fields: List[str],
) -> Dict[str, int]:
    result = {"inserted": 0, "updated": 0, "skipped": 0}

    source_rows = [dict(row) for row in source_conn.execute(f"SELECT rowid AS _rowid, * FROM {table_name}").fetchall()]
    target_rows = [dict(row) for row in target_conn.execute(f"SELECT rowid AS _rowid, * FROM {table_name}").fetchall()]

    target_map: Dict[str, Dict[str, Any]] = {}
    for row in target_rows:
        key = key_builder(row)
        if key:
            target_map[key] = row

    insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})"
    update_sql = f"UPDATE {table_name} SET " + ", ".join([f"{col} = ?" for col in columns]) + " WHERE rowid = ?"

    cur = target_conn.cursor()
    for source_row in source_rows:
        key = key_builder(source_row)
        if not key:
            result["skipped"] += 1
            continue

        target_row = target_map.get(key)
        if not target_row:
            values = [source_row.get(col, "") for col in columns]
            cur.execute(insert_sql, values)
            result["inserted"] += 1
            continue

        source_newer = _is_source_newer(source_row, target_row, datetime_fields)
        merged_values = [
            _merge_field_value(source_row.get(col, ""), target_row.get(col, ""), source_newer)
            for col in columns
        ]
        current_values = [target_row.get(col, "") for col in columns]
        if merged_values == current_values:
            result["skipped"] += 1
            continue

        cur.execute(update_sql, [*merged_values, target_row.get("_rowid")])
        result["updated"] += 1

    target_conn.commit()
    return result


def _merge_tasting_logs(source_conn: sqlite3.Connection, target_conn: sqlite3.Connection) -> Dict[str, int]:
    result = {"inserted": 0, "updated": 0, "skipped": 0}
    source_rows = [dict(row) for row in source_conn.execute("SELECT * FROM tasting_log").fetchall()]
    target_rows = [dict(row) for row in target_conn.execute("SELECT * FROM tasting_log").fetchall()]

    target_map = {str(row.get("id") or "").strip(): row for row in target_rows if str(row.get("id") or "").strip()}

    insert_sql = f"INSERT INTO tasting_log ({', '.join(TASTING_COLUMNS)}) VALUES ({', '.join(['?'] * len(TASTING_COLUMNS))})"
    update_sql = "UPDATE tasting_log SET " + ", ".join([f"{col} = ?" for col in TASTING_COLUMNS if col != "id"]) + " WHERE id = ?"

    cur = target_conn.cursor()
    for row in source_rows:
        row_id = str(row.get("id") or "").strip() or str(uuid.uuid4())
        row["id"] = row_id
        target_row = target_map.get(row_id)

        if not target_row:
            values = [row.get(col, "") for col in TASTING_COLUMNS]
            cur.execute(insert_sql, values)
            result["inserted"] += 1
            continue

        source_newer = _is_source_newer(row, target_row, ["created_at", "date"])
        merged = {
            col: _merge_field_value(row.get(col, ""), target_row.get(col, ""), source_newer)
            for col in TASTING_COLUMNS
        }
        changed = any(merged.get(col, "") != target_row.get(col, "") for col in TASTING_COLUMNS if col != "id")
        if not changed:
            result["skipped"] += 1
            continue

        cur.execute(update_sql, [*[merged.get(col, "") for col in TASTING_COLUMNS if col != "id"], row_id])
        result["updated"] += 1

    target_conn.commit()
    return result


def _merge_by_id(source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, table_name: str, columns: List[str]) -> Dict[str, int]:
    result = {"inserted": 0, "updated": 0, "skipped": 0}
    source_rows = [dict(row) for row in source_conn.execute(f"SELECT * FROM {table_name}").fetchall()]
    target_rows = [dict(row) for row in target_conn.execute(f"SELECT * FROM {table_name}").fetchall()]
    target_map = {str(row.get("id") or "").strip(): row for row in target_rows if str(row.get("id") or "").strip()}

    insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})"
    update_sql = f"UPDATE {table_name} SET " + ", ".join([f"{col} = ?" for col in columns if col != "id"]) + " WHERE id = ?"

    cur = target_conn.cursor()
    for row in source_rows:
        row_id = str(row.get("id") or "").strip()
        if not row_id:
            result["skipped"] += 1
            continue
        target_row = target_map.get(row_id)
        if not target_row:
            cur.execute(insert_sql, [row.get(col, "") for col in columns])
            result["inserted"] += 1
            continue

        source_newer = _is_source_newer(row, target_row, ["created_at"])
        merged = {
            col: _merge_field_value(row.get(col, ""), target_row.get(col, ""), source_newer)
            for col in columns
        }
        changed = any(merged.get(col, "") != target_row.get(col, "") for col in columns if col != "id")
        if not changed:
            result["skipped"] += 1
            continue

        cur.execute(update_sql, [*[merged.get(col, "") for col in columns if col != "id"], row_id])
        result["updated"] += 1

    target_conn.commit()
    return result


def _sync_images_additive(source_images_root: Path, target_images_root: Path) -> Dict[str, int]:
    report = {"copied": 0, "collisions": 0}
    if not source_images_root.exists() or not source_images_root.is_dir():
        return report

    target_images_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_images_root.rglob("*"):
        if not source_path.is_file():
            continue
        relative = source_path.relative_to(source_images_root)
        target_path = target_images_root / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists():
            report["collisions"] += 1
            continue
        shutil.copy2(source_path, target_path)
        report["copied"] += 1

    return report


def _upsert_env_values(updates: Dict[str, str]) -> None:
    lines: List[str] = []
    if ENV_FILE_PATH.exists():
        lines = ENV_FILE_PATH.read_text(encoding="utf-8").splitlines()

    seen = set()
    updated_lines: List[str] = []
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            updated_lines.append(line)
            continue
        key, _value = line.split("=", 1)
        key = key.strip()
        if key in updates:
            updated_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            updated_lines.append(line)

    for key, value in updates.items():
        if key not in seen:
            updated_lines.append(f"{key}={value}")

    ENV_FILE_PATH.write_text("\n".join(updated_lines).rstrip() + "\n", encoding="utf-8")
    for key, value in updates.items():
        os.environ[key] = value


def _merge_databases(source_db_path: Path, target_db_path: Path) -> Dict[str, Any]:
    source_conn = sqlite3.connect(source_db_path)
    source_conn.row_factory = sqlite3.Row
    target_conn = sqlite3.connect(target_db_path)
    target_conn.row_factory = sqlite3.Row
    try:
        _ensure_core_tables(source_conn)
        _ensure_core_tables(target_conn)

        alcohol_report = _merge_by_normalized_key(
            source_conn,
            target_conn,
            "alcohol_inventory",
            ALCOHOL_COLUMNS,
            lambda row: "|".join(
                [
                    normalize_name_key(row.get("Brand")),
                    normalize_name_key(row.get("Base_Liquor")),
                    normalize_name_key(row.get("Type")),
                ]
            ),
            [],
        )
        cocktail_report = _merge_by_normalized_key(
            source_conn,
            target_conn,
            "cocktail_notes",
            COCKTAIL_COLUMNS,
            lambda row: normalize_name_key(row.get("Cocktail_Name")),
            ["DatetimeAdded"],
        )
        tasting_report = _merge_tasting_logs(source_conn, target_conn)
        saved_view_report = _merge_by_id(source_conn, target_conn, "saved_views", SAVED_VIEW_COLUMNS)
        tag_report = _merge_by_id(source_conn, target_conn, "tags", TAG_COLUMNS)
        return {
            "alcohol_inventory": alcohol_report,
            "cocktail_notes": cocktail_report,
            "tasting_log": tasting_report,
            "saved_views": saved_view_report,
            "tags": tag_report,
        }
    finally:
        source_conn.close()
        target_conn.close()


def _schedule_backend_restart() -> None:
    python_exe = BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"
    python_path = python_exe if python_exe.exists() else Path(sys.executable)
    pythonw_path = python_path.with_name("pythonw.exe")
    launcher_python = pythonw_path if pythonw_path.exists() else python_path
    child_python = launcher_python
    launcher_code = (
        "import subprocess,time;"
        "time.sleep(4);"
        f"subprocess.Popen([{repr(str(child_python))},'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8002'],"
        f"cwd={repr(str(BACKEND_ROOT))},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,"
        "creationflags=(getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)|getattr(subprocess,'DETACHED_PROCESS',0)|getattr(subprocess,'CREATE_NO_WINDOW',0)))"
    )

    creation_flags = 0
    creation_flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    creation_flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    creation_flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)

    subprocess.Popen(
        [str(launcher_python), "-c", launcher_code],
        cwd=str(BACKEND_ROOT),
        creationflags=creation_flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    def _shutdown_later() -> None:
        time.sleep(1.8)
        os._exit(0)

    threading.Thread(target=_shutdown_later, daemon=True).start()


def _mirror_active_storage_to_local() -> None:
    global LAST_MIRROR_SYNC_AT

    active_db = DB_PATH.resolve()
    active_images = IMAGES_DIR.resolve()

    if active_db != LOCAL_DB_PATH and active_db.exists() and active_db.is_file():
        LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(active_db, LOCAL_DB_PATH)

    if active_images != LOCAL_IMAGES_DIR and active_images.exists() and active_images.is_dir():
        _sync_images_additive(active_images, LOCAL_IMAGES_DIR)

    LAST_MIRROR_SYNC_AT = _now_local_iso()


def build_local_twist_suggestions(payload: TwistRequest) -> list:
    base = payload.cocktail_name.strip() or "Your cocktail"
    constraints = payload.constraints.strip()
    prompt = payload.prompt.strip()

    if constraints:
        constraint_hint = f"Keep in mind: {constraints}."
    else:
        constraint_hint = "Keep the balance of sweet, sour, and spirit-forward notes."

    prompt_hint = prompt if prompt else "balanced but modern"

    suggestions = [
        {
            "name": f"{base} - Bright Split Citrus",
            "flavor_goal": "Lift aroma and acidity while keeping body intact.",
            "substitutions": [
                "Reduce simple syrup by 0.17 oz (5 ml).",
                "Add 0.34 oz (10 ml) fresh grapefruit juice plus 0.17 oz (5 ml) lemon juice.",
                "Add 1 dash orange bitters."
            ],
            "method": [
                "Add all ingredients to a shaker with cold dense ice.",
                "Shake hard for 10-12 seconds to push citrus oils into the drink.",
                "Double strain into a chilled coupe."
            ],
            "garnish_and_glass": "Express grapefruit peel over coupe, then discard peel.",
            "why_it_works": "The grapefruit-lemon split boosts brightness without becoming sharp, while bitters restore mid-palate depth.",
            "difficulty": "Easy",
            "risk_note": constraint_hint,
            "wild_card": "Mist glass with a tiny spray of saline (3:1 water:salt) for extra snap."
        },
        {
            "name": f"{base} - Botanical Dry Twist",
            "flavor_goal": f"Create a drier and more aromatic profile with {prompt_hint}.",
            "substitutions": [
                "Replace 0.5 oz (15 ml) of sweet modifier with a dry vermouth or fino sherry.",
                "Add 0.17 oz (5 ml) elderflower liqueur or yellow chartreuse.",
                "Optional: reduce total dilution by stirring 5 seconds less than usual."
            ],
            "method": [
                "Build in a mixing glass with quality ice.",
                "Stir 20-25 seconds until silky and chilled.",
                "Strain over a large clear rock in an old fashioned glass."
            ],
            "garnish_and_glass": "Lemon peel plus a slapped herb sprig (mint or thyme) in old fashioned glass.",
            "why_it_works": "Swapping part of the sweetness for fortified wine increases complexity and length while keeping balance.",
            "difficulty": "Medium",
            "risk_note": constraint_hint,
            "wild_card": "Rinse the glass with a peated whisky for a faint smoky frame."
        },
        {
            "name": f"{base} - Session Highball Remix",
            "flavor_goal": "Make a longer, lower-ABV serve that still tastes intentional and layered.",
            "substitutions": [
                "Cut base spirit by 0.5 oz (15 ml).",
                "Add 0.68 oz (20 ml) dry aperitif (e.g., Americano-style or dry vermouth).",
                "Top with 1.5-2 oz (45-60 ml) chilled soda or tonic depending on bitterness preference."
            ],
            "method": [
                "Build ingredients in a chilled highball over spear ice.",
                "Give one gentle lift stir to preserve carbonation.",
                "Taste and adjust with 2-3 drops saline or 0.17 oz (5 ml) citrus if needed."
            ],
            "garnish_and_glass": "Tall highball with citrus wheel and aromatic herb bouquet.",
            "why_it_works": "Lower proof increases drinkability while aperitif and saline keep structure and finish from feeling thin.",
            "difficulty": "Easy",
            "risk_note": "Carbonation can flatten sweetness quickly; taste after 60 seconds and rebalance.",
            "wild_card": "Float 0.17 oz (5 ml) overproof rum or mezcal for a split-aroma nose."
        }
    ]
    return suggestions


def extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("Model response was empty")

    fenced_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
    if fenced_match:
        return json.loads(fenced_match.group(1))

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not locate JSON object in model response")

    return json.loads(text[start : end + 1])


def normalize_twist_suggestions(parsed: Dict[str, Any]) -> list:
    def normalize_instruction_item(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, dict):
            original = str(value.get("original") or value.get("from") or "").strip()
            replacement = str(value.get("new") or value.get("to") or value.get("replacement") or "").strip()
            note = str(value.get("note") or value.get("details") or "").strip()

            if original and replacement:
                base = f"{original} -> {replacement}"
            elif replacement:
                base = replacement
            elif original:
                base = original
            else:
                base = ""

            if note:
                return f"{base} ({note})" if base else note
            return base

        if isinstance(value, (list, tuple)):
            return ", ".join(str(item).strip() for item in value if str(item).strip())

        return str(value).strip()

    raw_items = parsed.get("suggestions", []) if isinstance(parsed, dict) else []
    normalized = []
    for item in raw_items[:3]:
        if not isinstance(item, dict):
            continue

        substitutions = item.get("substitutions")
        if isinstance(substitutions, list):
            substitutions_list = [
                normalized_value
                for value in substitutions
                for normalized_value in [normalize_instruction_item(value)]
                if normalized_value
            ]
        elif substitutions:
            normalized_value = normalize_instruction_item(substitutions)
            substitutions_list = [normalized_value] if normalized_value else []
        else:
            substitutions_list = []

        method = item.get("method")
        if isinstance(method, list):
            method_list = [
                normalized_value
                for value in method
                for normalized_value in [normalize_instruction_item(value)]
                if normalized_value
            ]
        elif method:
            normalized_value = normalize_instruction_item(method)
            method_list = [normalized_value] if normalized_value else []
        else:
            method_list = []

        normalized.append(
            {
                "name": str(item.get("name") or "Twist Concept").strip(),
                "flavor_goal": str(item.get("flavor_goal") or "").strip(),
                "substitutions": substitutions_list,
                "method": method_list,
                "garnish_and_glass": str(item.get("garnish_and_glass") or "").strip(),
                "why_it_works": str(item.get("why_it_works") or "").strip(),
                "difficulty": str(item.get("difficulty") or "").strip(),
                "risk_note": str(item.get("risk_note") or "").strip(),
                "wild_card": str(item.get("wild_card") or "").strip(),
            }
        )

    if not normalized:
        raise ValueError("No valid twist suggestions were found in model response")

    return normalized


def call_groq_twist_suggestions(payload: TwistRequest, api_key: str) -> Dict[str, Any]:
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    timeout_seconds = float(os.getenv("GROQ_TIMEOUT_SECONDS", "20"))

    prompt_parts = [
        f"Cocktail: {payload.cocktail_name}",
        f"Ingredients: {payload.ingredients or 'Unknown'}",
        f"Constraints: {payload.constraints or 'None'}",
        f"Flavor direction: {payload.prompt or 'Balanced and modern'}",
        "Return exactly 3 twist concepts as STRICT JSON only.",
        "Each concept must include: name, flavor_goal, substitutions (list), method (list), garnish_and_glass, why_it_works, difficulty, risk_note, wild_card.",
        "substitutions and method must be arrays of plain strings only (no objects, no nested JSON).",
        "Style guide: include one conservative riff, one modern bar riff, and one adventurous riff.",
        "For any ingredient amount, always include BOTH units in this format: X oz (Y ml).",
        "Prioritize practical measurements and actionable steps over general advice.",
        "JSON shape: {\"suggestions\":[{...},{...},{...}]}"
    ]

    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a cocktail R&D assistant creating detailed, adventurous but practical recipe twists for experienced home bartenders. Whenever a quantity is used, provide both oz and ml. Output valid JSON only."
            },
            {
                "role": "user",
                "content": "\n".join(prompt_parts)
            }
        ],
        "temperature": 0.9
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        json=body,
        headers=headers,
        timeout=timeout_seconds
    )
    response.raise_for_status()
    payload_json = response.json()

    choices = payload_json.get("choices", [])
    if not choices:
        raise ValueError("Groq response had no choices")

    content = choices[0].get("message", {}).get("content", "").strip()
    if not content:
        raise ValueError("Groq response content was empty")

    parsed = extract_json_object(content)
    suggestions = normalize_twist_suggestions(parsed)
    return {"model": model, "suggestions": suggestions}


def call_gemini_twist_suggestions(payload: TwistRequest, api_key: str) -> Dict[str, Any]:
    configured_model_raw = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    configured_model = re.sub(r"^\s*GEMINI_MODEL\s*=\s*", "", configured_model_raw).strip().strip('"\'')
    if not configured_model:
        configured_model = "gemini-2.0-flash"

    timeout_seconds = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "20"))

    candidate_models = []
    for model_name in [configured_model, "gemini-2.0-flash"]:
        if model_name and model_name not in candidate_models:
            candidate_models.append(model_name)

    prompt_parts = [
        f"Cocktail: {payload.cocktail_name}",
        f"Ingredients: {payload.ingredients or 'Unknown'}",
        f"Constraints: {payload.constraints or 'None'}",
        f"Flavor direction: {payload.prompt or 'Balanced and modern'}",
        "Return exactly 3 twist concepts as STRICT JSON only.",
        "Each concept must include: name, flavor_goal, substitutions (list), method (list), garnish_and_glass, why_it_works, difficulty, risk_note, wild_card.",
        "substitutions and method must be arrays of plain strings only (no objects, no nested JSON).",
        "Style guide: include one conservative riff, one modern bar riff, and one adventurous riff.",
        "For any ingredient amount, always include BOTH units in this format: X oz (Y ml).",
        "Prioritize practical measurements and actionable steps over general advice.",
        "JSON shape: {\"suggestions\":[{...},{...},{...}]}"
    ]

    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "You are a cocktail R&D assistant creating detailed, adventurous but practical recipe twists for experienced home bartenders. Whenever a quantity is used, provide both oz and ml. Output valid JSON only.\n" + "\n".join(prompt_parts)
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 512,
        },
    }

    payload_json = None
    selected_model = None
    errors = []
    saw_quota_limit = False
    saw_not_found = False
    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        response = requests.post(
            url,
            params={"key": api_key},
            json=body,
            timeout=timeout_seconds,
        )
        if response.ok:
            payload_json = response.json()
            selected_model = model
            break

        errors.append(f"{model}:{response.status_code}")
        if response.status_code == 429:
            saw_quota_limit = True
        if response.status_code == 404:
            saw_not_found = True

    if payload_json is None:
        if saw_quota_limit:
            raise ValueError("Gemini quota/rate limit reached (429). Please retry later or increase quota")
        if saw_not_found:
            raise ValueError("Configured Gemini model is unavailable for this API key/project")
        raise ValueError("Gemini request failed for models " + ",".join(errors))

    candidates = payload_json.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini response had no candidates")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "\n".join(part.get("text", "") for part in parts if part.get("text", "")).strip()
    if not text:
        raise ValueError("Gemini response content was empty")

    parsed = extract_json_object(text)
    suggestions = normalize_twist_suggestions(parsed)
    return {"model": selected_model, "suggestions": suggestions}


def parse_price_nzd(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def round2(value: Any) -> Any:
    if value is None:
        return None
    return round(float(value), 2)


def parse_float(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_country_key(country: str) -> str:
    key = re.sub(r"[^a-z0-9]+", " ", country.lower()).strip()
    return re.sub(r"\s+", " ", key)


def resolve_country_iso2(country: str) -> str:
    normalized_key = _normalize_country_key(country)
    if not normalized_key:
        raise HTTPException(status_code=400, detail="country is required")

    override = COUNTRY_TO_ISO2_OVERRIDES.get(normalized_key)
    if override:
        return override

    encoded = requests.utils.quote(country.strip())
    candidates = [
        f"https://restcountries.com/v3.1/name/{encoded}?fields=cca2,name",
    ]

    for url in candidates:
        try:
            response = requests.get(url, timeout=12)
        except requests.RequestException:
            continue

        if not response.ok:
            continue

        try:
            payload = response.json()
        except ValueError:
            continue

        if not isinstance(payload, list) or not payload:
            continue

        exact_match = None
        partial_match = None
        for item in payload:
            if not isinstance(item, dict):
                continue

            cca2 = str(item.get("cca2") or "").strip().lower()
            if not re.fullmatch(r"[a-z]{2}", cca2):
                continue

            common_name = str((item.get("name") or {}).get("common") or "").strip()
            normalized_common = _normalize_country_key(common_name)

            if normalized_common == normalized_key:
                exact_match = cca2
                break

            if normalized_key in normalized_common and not partial_match:
                partial_match = cca2

        if exact_match:
            return exact_match
        if partial_match:
            return partial_match

    raise HTTPException(status_code=404, detail=f"Could not resolve country: {country}")


def resolve_country_flag(country: str) -> Tuple[str, str, bool]:
    iso2 = resolve_country_iso2(country)
    FLAGS_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{iso2}.png"
    local_path = FLAGS_DIR / filename
    relative_path = f"images/flags/{filename}"

    if local_path.exists() and local_path.is_file() and local_path.stat().st_size > 0:
        return iso2, relative_path, False

    download_url = f"https://flagcdn.com/w160/{iso2}.png"
    try:
        response = requests.get(download_url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to download flag image: {exc}") from exc

    if not response.content:
        raise HTTPException(status_code=502, detail="Flag image download returned empty content")

    local_path.write_bytes(response.content)
    return iso2, relative_path, True


def _slugify_filename_part(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower().strip())).strip("-")


def _sanitize_image_extension(value: str) -> str:
    ext = value.lower().strip().lstrip(".")
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return "jpg" if ext == "jpeg" else ext
    return "png"


def _infer_extension(image_url: str, content_type: str) -> str:
    parsed = urlparse(image_url)
    suffix = Path(parsed.path).suffix.lower().lstrip(".")
    if suffix in ALLOWED_IMAGE_EXTENSIONS:
        return _sanitize_image_extension(suffix)

    mime = content_type.lower().strip()
    if "jpeg" in mime or "jpg" in mime:
        return "jpg"
    if "webp" in mime:
        return "webp"
    if "gif" in mime:
        return "gif"
    return "png"


def _is_supported_image_type(image_url: str, content_type: str) -> bool:
    mime = content_type.lower().strip()
    if mime.startswith("image/"):
        return any(part in mime for part in ("png", "jpeg", "jpg", "webp", "gif"))

    parsed = urlparse(image_url)
    suffix = Path(parsed.path).suffix.lower().lstrip(".")
    return suffix in ALLOWED_IMAGE_EXTENSIONS


def _is_allowed_wikimedia_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False

    host = (parsed.hostname or "").lower()
    if not host:
        return False

    return any(host == suffix or host.endswith(f".{suffix}") for suffix in WIKIMEDIA_ALLOWED_HOST_SUFFIXES)


def _build_liquor_filename(brand: str, liquor_type: str, extension: str) -> str:
    brand_slug = _slugify_filename_part(brand)
    type_slug = _slugify_filename_part(liquor_type)
    if not brand_slug:
        raise HTTPException(status_code=400, detail="brand is required")

    base = f"{brand_slug}-{type_slug}" if type_slug else brand_slug
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    ext = _sanitize_image_extension(extension)
    return f"{base}-{ts}.{ext}"


def _extract_taste_hint(text: str) -> str:
    if not text:
        return ""

    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    keywords = ("taste", "tasting", "flavor", "flavour", "aroma", "notes", "palate", "finish")
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            return sentence.strip()[:260]

    return cleaned[:200]


def normalize_name_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _extract_abv_hint(text: str) -> str:
    if not text:
        return ""

    patterns = [
        r"(?:abv|alcohol(?: by volume)?|proof)\s*(?:is|of|at)?\s*(\d{1,2}(?:\.\d+)?)\s*%",
        r"(\d{1,2}(?:\.\d+)?)\s*%\s*(?:abv|alcohol(?: by volume)?)",
    ]
    lowered = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            return f"{match.group(1)}%"

    proof_match = re.search(r"(\d{2,3}(?:\.\d+)?)\s*[- ]?proof", lowered)
    if proof_match:
        try:
            proof_value = float(proof_match.group(1))
            if proof_value > 0:
                return f"{proof_value / 2:.1f}%".replace(".0%", "%")
        except ValueError:
            pass

    return ""


def _clean_html_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = text.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s+", " ", text).strip()


def _extract_country_hint_from_text(text: str) -> str:
    lowered = str(text or "").lower()
    if not lowered:
        return ""

    country_candidates = [
        "england", "scotland", "ireland", "france", "spain", "italy", "germany", "japan",
        "mexico", "united states", "usa", "canada", "new zealand", "australia", "caribbean",
        "jamaica", "barbados", "trinidad", "guatemala", "venezuela", "cuba", "dominican republic",
    ]
    for country in country_candidates:
        if re.search(rf"\b(from|in|of|produced in|distilled in)\s+{re.escape(country)}\b", lowered):
            return country.title().replace("Usa", "USA")
    return ""


def _base_family_from_value(base_liquor: str) -> str:
    normalized = str(base_liquor or "").strip().lower()
    if "gin" in normalized:
        return "gin"
    if any(term in normalized for term in ("rum", "rhum", "cachaca")):
        return "rum"
    if "tequila" in normalized:
        return "tequila"
    if "mezcal" in normalized:
        return "mezcal"
    if "vodka" in normalized:
        return "vodka"
    if any(term in normalized for term in ("brandy", "cognac", "armagnac")):
        return "brandy"
    if any(term in normalized for term in ("whiskey", "whisky", "scotch", "bourbon", "rye")):
        return "whiskey"
    if any(term in normalized for term in ("liqueur", "liquor", "amaro", "aperitif", "aperitivo")):
        return "liqueur"
    return ""


def _suggest_types_from_text(base_liquor: str, text: str) -> List[str]:
    family = _base_family_from_value(base_liquor)
    lowered = str(text or "").lower()
    suggestions: List[str] = []

    keyword_map = [
        ("London Dry Gin", ["london dry"]),
        ("Old Tom Gin", ["old tom"]),
        ("Plymouth Gin", ["plymouth"]),
        ("White Rum", ["white rum", "light rum"]),
        ("Dark Rum", ["dark rum", "black rum"]),
        ("Spiced Rum", ["spiced rum"]),
        ("Aged Rum", ["aged rum"]),
        ("Blanco Tequila", ["blanco", "plata", "silver tequila"]),
        ("Reposado Tequila", ["reposado"]),
        ("Anejo Tequila", ["anejo", "añejo"]),
        ("Joven Mezcal", ["joven"]),
        ("Reposado Mezcal", ["mezcal reposado"]),
        ("Anejo Mezcal", ["mezcal anejo", "mezcal añejo"]),
        ("Bourbon Whiskey", ["bourbon"]),
        ("Rye Whiskey", ["rye whiskey", "rye whisky"]),
        ("Irish Whiskey", ["irish whiskey"]),
        ("Scotch Whisky", ["scotch", "single malt"]),
        ("Cognac", ["cognac"]),
        ("Armagnac", ["armagnac"]),
        ("Amaro", ["amaro"]),
        ("Orange Liqueur", ["triple sec", "curaçao", "curacao", "orange liqueur"]),
    ]

    for style, keys in keyword_map:
        if any(key in lowered for key in keys):
            suggestions.append(style)

    defaults = {
        "gin": ["London Dry Gin", "Distilled Gin", "Old Tom Gin"],
        "rum": ["White Rum", "Dark Rum", "Spiced Rum", "Aged Rum"],
        "tequila": ["Blanco Tequila", "Reposado Tequila", "Anejo Tequila"],
        "mezcal": ["Joven Mezcal", "Reposado Mezcal", "Anejo Mezcal"],
        "vodka": ["Classic Vodka", "Flavored Vodka"],
        "brandy": ["Brandy", "Cognac", "Armagnac"],
        "whiskey": ["Whiskey", "Bourbon Whiskey", "Rye Whiskey", "Scotch Whisky", "Irish Whiskey"],
        "liqueur": ["Liqueur", "Amaro", "Bitter Aperitif", "Orange Liqueur"],
    }

    suggestions.extend(defaults.get(family, []))
    unique = []
    for item in suggestions:
        if item and item not in unique:
            unique.append(item)
    return unique[:10]


def _lookup_wikipedia_extract(query: str) -> Tuple[str, str, str, str]:
    try:
        search_res = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": "1",
                "format": "json",
            },
            headers=WEB_LOOKUP_HEADERS,
            timeout=20,
        )
        search_res.raise_for_status()
        search_payload = search_res.json()
    except (requests.RequestException, ValueError):
        return "", "", "", ""

    search_items = ((search_payload.get("query") or {}).get("search") or [])
    if not search_items:
        return "", "", "", ""

    title = str(search_items[0].get("title") or "").strip()
    if not title:
        return "", "", "", ""

    try:
        summary_res = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}"
            ,
            headers=WEB_LOOKUP_HEADERS,
            timeout=20,
        )
        summary_res.raise_for_status()
        summary_payload = summary_res.json()
    except (requests.RequestException, ValueError):
        return title, "", f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe=':_-()')}", ""

    extract = str(summary_payload.get("extract") or "").strip()
    source_url = str(((summary_payload.get("content_urls") or {}).get("desktop") or {}).get("page") or "").strip()
    wikibase_id = str(summary_payload.get("wikibase_item") or "").strip()
    if not source_url:
        source_url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe=':_-()')}"
    return title, extract, source_url, wikibase_id


def _lookup_wikidata_hints(wikibase_id: str) -> Tuple[str, str, str]:
    if not wikibase_id:
        return "", "", ""

    try:
        res = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbgetentities",
                "ids": wikibase_id,
                "props": "claims|labels",
                "languages": "en",
                "format": "json",
            },
            headers=WEB_LOOKUP_HEADERS,
            timeout=20,
        )
        res.raise_for_status()
        payload = res.json()
    except (requests.RequestException, ValueError):
        return "", "", ""

    entity = (payload.get("entities") or {}).get(wikibase_id) or {}
    claims = entity.get("claims") or {}

    country_id = ""
    for claim_key in ("P495", "P17"):
        claim_list = claims.get(claim_key) or []
        for item in claim_list:
            value = (((item.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {})
            cid = str(value.get("id") or "").strip()
            if cid.startswith("Q"):
                country_id = cid
                break
        if country_id:
            break

    country_hint = ""
    if country_id:
        try:
            country_res = requests.get(
                "https://www.wikidata.org/w/api.php",
                params={
                    "action": "wbgetentities",
                    "ids": country_id,
                    "props": "labels",
                    "languages": "en",
                    "format": "json",
                },
                headers=WEB_LOOKUP_HEADERS,
                timeout=20,
            )
            country_res.raise_for_status()
            country_payload = country_res.json()
            country_hint = str(
                ((((country_payload.get("entities") or {}).get(country_id) or {}).get("labels") or {}).get("en") or {}).get("value")
                or ""
            ).strip()
        except (requests.RequestException, ValueError):
            country_hint = ""

    abv_hint = ""
    abv_claims = claims.get("P2665") or []
    for item in abv_claims:
        value = (((item.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {})
        amount = str(value.get("amount") or "").strip()
        amount = amount.lstrip("+")
        if amount:
            try:
                abv_float = float(amount)
                abv_hint = f"{abv_float:.1f}%".replace(".0%", "%")
                break
            except ValueError:
                continue

    source_url = f"https://www.wikidata.org/wiki/{wikibase_id}"
    return country_hint, abv_hint, source_url


def _lookup_price_nzd_hint(query: str) -> str:
    try:
        res = requests.get(
            "https://duckduckgo.com/html/",
            params={"q": query},
            headers=WEB_LOOKUP_HEADERS,
            timeout=20,
        )
        res.raise_for_status()
        html = res.text
    except requests.RequestException:
        return ""

    patterns = [
        r"NZ\$\s*(\d+(?:\.\d{1,2})?)",
        r"\$\s*(\d+(?:\.\d{1,2})?)\s*NZD",
        r"(\d+(?:\.\d{1,2})?)\s*NZD",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, html, flags=re.IGNORECASE)
        for item in matches[:5]:
            candidate = str(item).strip()
            try:
                amount = float(candidate)
                if 8 <= amount <= 5000:
                    return f"{amount:.2f}".rstrip("0").rstrip(".")
            except ValueError:
                continue
    return ""


def _lookup_substitute_hint(brand: str, base_liquor: str, alcohol_type: str) -> str:
    query = " ".join(part for part in ["alternative to", brand, alcohol_type or base_liquor, "bottle"] if part)
    try:
        res = requests.get(
            "https://duckduckgo.com/html/",
            params={"q": query},
            headers=WEB_LOOKUP_HEADERS,
            timeout=20,
        )
        res.raise_for_status()
        html = res.text
    except requests.RequestException:
        return ""

    brand_tokens = set(normalize_name_key(brand).split())
    title_matches = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL)
    for raw_title in title_matches[:8]:
        title = _clean_html_text(raw_title)
        if not title:
            continue

        for chunk in re.split(r"\s[\-|\|:]\s", title):
            candidate = chunk.strip()
            if len(candidate) < 4:
                continue
            if re.search(r"\b(alternative|substitute|review|price|buy|best|vs|comparison|shop|online|liquorland|superliquor|master of malt|drizly)\b", candidate, flags=re.IGNORECASE):
                continue

            words = normalize_name_key(candidate).split()
            if not words:
                continue
            overlap = len(set(words) & brand_tokens)
            if overlap >= max(1, len(brand_tokens) // 2):
                continue

            if len(words) >= 2:
                return candidate[:80]

    return ""


@app.get("/alcohol-web-hints")
def alcohol_web_hints(
    brand: str = Query(..., description="Alcohol brand"),
    base_liquor: str = Query("", description="Primary liquor family"),
    alcohol_type: str = Query("", alias="type", description="Current alcohol type"),
) -> Dict[str, Any]:
    brand_value = brand.strip()
    base_value = base_liquor.strip()
    type_value = alcohol_type.strip()

    if not brand_value:
        raise HTTPException(status_code=400, detail="brand is required")

    lookup_query = " ".join(part for part in [brand_value, base_value, type_value, "liquor"] if part)
    title, extract, wiki_source, wikibase_id = _lookup_wikipedia_extract(lookup_query)
    country_wikidata, abv_wikidata, wikidata_source = _lookup_wikidata_hints(wikibase_id)
    taste_hint = _extract_taste_hint(extract)
    abv_hint = abv_wikidata or _extract_abv_hint(extract)
    country_hint = country_wikidata or _extract_country_hint_from_text(extract)
    price_hint = _lookup_price_nzd_hint(f"{brand_value} {base_value} price NZD")
    substitute_hint = _lookup_substitute_hint(brand_value, base_value, type_value)
    suggested_types = _suggest_types_from_text(base_value, f"{title}. {extract}")

    sources = []
    if wiki_source:
        sources.append({"name": "Wikipedia", "url": wiki_source})
    if wikidata_source:
        sources.append({"name": "Wikidata", "url": wikidata_source})
    if price_hint:
        sources.append({"name": "Web Search", "url": "https://duckduckgo.com/"})

    return {
        "brand": brand_value,
        "base_liquor": base_value,
        "type": type_value,
        "suggested_types": suggested_types,
        "taste_hint": taste_hint,
        "abv_hint": abv_hint,
        "country_hint": country_hint,
        "price_nzd_hint": price_hint,
        "substitute_hint": substitute_hint,
        "sources": sources,
    }


@app.get("/alcohol-image-candidates")
def alcohol_image_candidates(
    brand: str = Query(..., description="Alcohol brand"),
    alcohol_type: str = Query("", alias="type", description="Alcohol type"),
    limit: int = Query(8, ge=1, le=15),
) -> Dict[str, Any]:
    brand_value = brand.strip()
    type_value = alcohol_type.strip()
    if not brand_value:
        raise HTTPException(status_code=400, detail="brand is required")

    search_query = " ".join(part for part in [brand_value, type_value, "bottle"] if part)
    try:
        response = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": search_query,
                "gsrnamespace": "6",
                "gsrlimit": str(limit),
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "iiurlwidth": "360",
                "format": "json",
            },
            headers=WIKIMEDIA_HEADERS,
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to search Wikimedia candidates: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Wikimedia search returned invalid JSON") from exc

    pages = (payload.get("query") or {}).get("pages") or {}
    items = []
    for page in pages.values():
        title = str(page.get("title") or "").strip()
        image_info = ((page.get("imageinfo") or [None])[0] or {})
        image_url = str(image_info.get("url") or "").strip()
        thumbnail_url = str(image_info.get("thumburl") or image_url).strip()
        mime = str(image_info.get("mime") or "").strip()

        if not title or not image_url:
            continue
        if not _is_allowed_wikimedia_url(image_url):
            continue
        if not _is_supported_image_type(image_url, mime):
            continue

        source_page_url = f"https://commons.wikimedia.org/wiki/{quote(title.replace(' ', '_'), safe=':_-()')}"
        items.append(
            {
                "title": title,
                "thumbnail_url": thumbnail_url,
                "image_url": image_url,
                "source_page_url": source_page_url,
                "mime": mime,
            }
        )

    return {
        "query": search_query,
        "items": items,
    }


@app.post("/alcohol-image-save-from-url")
def alcohol_image_save_from_url(payload: Dict[str, Any]) -> Dict[str, Any]:
    brand = str(payload.get("brand") or "").strip()
    alcohol_type = str(payload.get("type") or "").strip()
    image_url = str(payload.get("image_url") or "").strip()

    if not brand:
        raise HTTPException(status_code=400, detail="brand is required")
    if not image_url:
        raise HTTPException(status_code=400, detail="image_url is required")
    if not _is_allowed_wikimedia_url(image_url):
        raise HTTPException(status_code=400, detail="image_url must be a Wikimedia/Wikipedia URL")

    try:
        response = requests.get(image_url, headers=WIKIMEDIA_HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Failed to download selected image: {exc}") from exc

    if not response.content:
        raise HTTPException(status_code=502, detail="Downloaded image payload is empty")
    if not _is_supported_image_type(image_url, str(response.headers.get("content-type") or "")):
        raise HTTPException(status_code=400, detail="Selected URL must point to a supported image type")

    extension = _infer_extension(image_url, str(response.headers.get("content-type") or ""))
    filename = _build_liquor_filename(brand, alcohol_type, extension)

    if USE_SUPABASE:
        key = f"liquors/{filename}"
        _upload_to_supabase_storage(key, response.content, str(response.headers.get("content-type") or "application/octet-stream"))

        def _mirror_image_save() -> None:
            target_dir = ALLOWED_UPLOAD_CATEGORIES["liquors"]
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / filename
            target_path.write_bytes(response.content)

        _mirror_local("alcohol_image_save_from_url", _mirror_image_save)
        return {
            "image_path": f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{key}",
            "image_key": key,
            "filename": filename,
        }

    target_dir = ALLOWED_UPLOAD_CATEGORIES["liquors"]
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    target_path.write_bytes(response.content)

    return {
        "image_path": f"images/liquors/{filename}",
        "filename": filename,
    }


@app.post("/image-upload")
def upload_image(payload: Dict[str, Any]) -> Dict[str, str]:
    category = str(payload.get("category") or "").strip().lower()
    raw_filename = str(payload.get("filename") or "").strip()
    data_base64 = str(payload.get("data_base64") or "").strip()

    if category not in ALLOWED_UPLOAD_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid image category")

    if not raw_filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    safe_filename = Path(raw_filename).name
    safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "-", safe_filename)
    if not safe_filename or safe_filename in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not data_base64:
        raise HTTPException(status_code=400, detail="Image data is required")

    if "," in data_base64:
        data_base64 = data_base64.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(data_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Invalid base64 image payload")

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Decoded image payload is empty")

    if USE_SUPABASE:
        key = f"{category}/{safe_filename}"
        _upload_to_supabase_storage(key, image_bytes, "application/octet-stream")

        def _mirror_uploaded_image() -> None:
            target_dir = ALLOWED_UPLOAD_CATEGORIES[category]
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / safe_filename
            target_path.write_bytes(image_bytes)

        _mirror_local("image_upload", _mirror_uploaded_image)
        return {"image_path": f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{key}"}

    target_dir = ALLOWED_UPLOAD_CATEGORIES[category]
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / safe_filename
    target_path.write_bytes(image_bytes)

    return {"image_path": f"images/{category}/{safe_filename}"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def mirror_storage_middleware(request, call_next):
    response = await call_next(request)

    path = request.url.path or ""
    if (
        request.method in {"POST", "PUT", "DELETE"}
        and response.status_code < 400
        and not path.startswith("/settings/storage")
    ):
        try:
            _mirror_active_storage_to_local()
        except Exception:
            pass

    return response


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/", include_in_schema=False)
def web_root() -> Any:
    index_path = FRONTEND_DIST_DIR / "index.html"
    if index_path.exists() and index_path.is_file():
        return FileResponse(str(index_path))
    return {
        "status": "ok",
        "message": "Frontend build not found. Build web/frontend (npm run build) to serve UI from backend.",
    }


@app.get("/meta/db-path")
def db_path() -> Dict[str, str]:
    return {"db_path": str(DB_PATH)}


@app.get("/settings/storage")
def get_storage_settings() -> Dict[str, Any]:
    _assert_storage_controls_available()
    db_path_value = DB_PATH.resolve()
    images_path_value = IMAGES_DIR.resolve()
    local_db_path_value = LOCAL_DB_PATH.resolve()
    local_images_path_value = LOCAL_IMAGES_DIR.resolve()
    root_path_value = _storage_root_from_paths(db_path_value, images_path_value)
    dual_save_enabled = db_path_value != local_db_path_value or images_path_value != local_images_path_value
    backup_configured = dual_save_enabled
    return {
        "root_path": str(root_path_value),
        "db_path": str(db_path_value),
        "images_path": str(images_path_value),
        "local_db_path": str(local_db_path_value),
        "local_images_path": str(local_images_path_value),
        "dual_save_enabled": dual_save_enabled,
        "backup_configured": backup_configured,
        "active_db_last_write_at": _path_last_modified_iso(db_path_value),
        "local_db_last_write_at": _path_last_modified_iso(local_db_path_value),
        "last_mirror_sync_at": LAST_MIRROR_SYNC_AT,
        "db_source": "env" if str(os.getenv("COCKTAIL_DB_PATH", "")).strip() else "default",
        "images_source": "env" if str(os.getenv("COCKTAIL_IMAGES_PATH", "")).strip() else "default",
    }


@app.post("/settings/storage/browse")
def browse_storage_folder(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    _assert_storage_controls_available()
    initial_path = str(payload.get("initial_path") or "").strip()

    safe_initial = initial_path or str(REPO_ROOT)
    escaped_initial = safe_initial.replace("'", "''")
    ps_script = "\n".join([
        "Add-Type -AssemblyName System.Windows.Forms",
        "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog",
        "$dialog.Description = 'Select storage root folder'",
        "$dialog.ShowNewFolderButton = $true",
        f"$dialog.SelectedPath = '{escaped_initial}'",
        "$result = $dialog.ShowDialog()",
        "if ($result -eq [System.Windows.Forms.DialogResult]::OK) {",
        "  Write-Output $dialog.SelectedPath",
        "}",
    ])

    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", ps_script],
            cwd=str(BACKEND_ROOT),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=408, detail="Folder picker timed out. Please try again.") from exc
    except Exception as exc:  # pragma: no cover - platform dependency
        raise HTTPException(status_code=500, detail=f"Failed to open folder picker: {exc}") from exc

    if completed.returncode != 0:
        stderr = str(completed.stderr or "").strip()
        raise HTTPException(status_code=500, detail=stderr or "Folder picker failed.")

    selected = str(completed.stdout or "").strip()
    return {"selected_path": selected}


@app.post("/settings/storage/mirror-now")
def mirror_storage_now() -> Dict[str, Any]:
    _assert_storage_controls_available()
    try:
        _mirror_active_storage_to_local()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to mirror active storage: {exc}") from exc

    return {
        "status": "mirrored",
        "last_mirror_sync_at": LAST_MIRROR_SYNC_AT,
        "local_db_path": str(LOCAL_DB_PATH),
        "local_images_path": str(LOCAL_IMAGES_DIR),
    }


@app.post("/settings/storage/preflight")
def storage_preflight(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    _assert_storage_controls_available()
    root_input = str(payload.get("root_path") or "").strip()
    target_root, target_db_path, target_images_path = _resolve_target_paths(root_input)
    _assert_directory_writable(target_root)

    source_db_path = DB_PATH.resolve()
    source_images_path = IMAGES_DIR.resolve()

    source_stats = _collect_db_stats(source_db_path)
    target_stats = _collect_db_stats(target_db_path)

    empty_location = _is_empty_location(target_db_path, target_images_path)

    return {
        "target": {
            "root_path": str(target_root),
            "db_path": str(target_db_path),
            "images_path": str(target_images_path),
        },
        "source": {
            "db_path": str(source_db_path),
            "images_path": str(source_images_path),
        },
        "empty_location": empty_location,
        "action_preview": "copy_current" if empty_location else "merge",
        "db_stats": {
            "source": source_stats,
            "target": target_stats,
        },
    }


@app.post("/settings/storage/apply")
def apply_storage_settings(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    _assert_storage_controls_available()
    root_input = str(payload.get("root_path") or "").strip()
    if not root_input:
        raise HTTPException(status_code=400, detail="root_path is required")

    target_root, target_db_path, target_images_path = _resolve_target_paths(root_input)
    _assert_directory_writable(target_root)

    source_db_path = DB_PATH.resolve()
    source_images_path = IMAGES_DIR.resolve()

    backup_dir = target_root / "backup"
    backup_current_db = _backup_file(source_db_path, backup_dir, "current-db")
    backup_target_db = _backup_file(target_db_path, backup_dir, "target-db")

    empty_location = _is_empty_location(target_db_path, target_images_path)
    target_images_path.mkdir(parents=True, exist_ok=True)
    (target_images_path / "liquors").mkdir(parents=True, exist_ok=True)
    (target_images_path / "cocktails").mkdir(parents=True, exist_ok=True)
    (target_images_path / "flags").mkdir(parents=True, exist_ok=True)

    if empty_location:
        if source_db_path.exists() and source_db_path.is_file():
            shutil.copy2(source_db_path, target_db_path)
        image_report = _sync_images_additive(source_images_path, target_images_path)
        db_report = {
            "mode": "copy_current",
            "alcohol_inventory": {"inserted": 0, "updated": 0, "skipped": 0},
            "cocktail_notes": {"inserted": 0, "updated": 0, "skipped": 0},
            "tasting_log": {"inserted": 0, "updated": 0, "skipped": 0},
            "saved_views": {"inserted": 0, "updated": 0, "skipped": 0},
            "tags": {"inserted": 0, "updated": 0, "skipped": 0},
        }
    else:
        if not target_db_path.exists():
            if source_db_path.exists() and source_db_path.is_file():
                shutil.copy2(source_db_path, target_db_path)
            else:
                sqlite3.connect(target_db_path).close()

        db_report = _merge_databases(source_db_path, target_db_path)
        db_report["mode"] = "merge"
        image_report = _sync_images_additive(source_images_path, target_images_path)

    _upsert_env_values(
        {
            "COCKTAIL_DB_PATH": str(target_db_path),
            "COCKTAIL_IMAGES_PATH": str(target_images_path),
        }
    )

    result = {
        "status": "applied",
        "target": {
            "root_path": str(target_root),
            "db_path": str(target_db_path),
            "images_path": str(target_images_path),
        },
        "empty_location": empty_location,
        "backups": {
            "current_db": backup_current_db,
            "target_db": backup_target_db,
            "backup_dir": str(backup_dir),
        },
        "db_report": db_report,
        "image_report": image_report,
        "restart": "scheduled",
    }

    _schedule_backend_restart()
    return result


@app.get("/meta/counts", response_model=CountsResponse)
def counts() -> CountsResponse:
    if USE_SUPABASE:
        alcohol_row = _pg_fetch_one("SELECT COUNT(*) AS value FROM alcohol_inventory")
        cocktail_row = _pg_fetch_one("SELECT COUNT(*) AS value FROM cocktail_notes")
        return CountsResponse(
            alcohol_inventory=int((alcohol_row or {}).get("value") or 0),
            cocktail_notes=int((cocktail_row or {}).get("value") or 0),
        )

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM alcohol_inventory")
        alcohol_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM cocktail_notes")
        cocktail_count = cur.fetchone()[0]
    return CountsResponse(alcohol_inventory=alcohol_count, cocktail_notes=cocktail_count)


@app.get("/meta/flag-by-country")
def get_flag_by_country(country: str = Query(..., description="Country name from alcohol record")) -> Dict[str, Any]:
    requested_country = country.strip()
    if not requested_country:
        raise HTTPException(status_code=400, detail="country is required")

    iso2, image_path, downloaded = resolve_country_flag(requested_country)
    return {
        "country": requested_country,
        "iso2": iso2,
        "image_path": image_path,
        "downloaded": downloaded,
    }


@app.get("/analytics/cost-insights")
def analytics_cost_insights() -> Dict[str, Any]:
    if USE_SUPABASE:
        alcohol_rows = _pg_fetch_all(
            f"SELECT {_pg_columns(['Brand', 'Base_Liquor', 'Price_NZD_700ml'])} FROM alcohol_inventory"
        )
        cocktail_rows = _pg_fetch_all(
            f"SELECT {_pg_columns(['Cocktail_Name', 'Ingredients', 'Base_spirit_1', 'Base_spirit_2'])} FROM cocktail_notes"
        )
        tasting_rows = _pg_fetch_all("SELECT date, cocktail_name FROM tasting_log")
    else:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT Brand, Base_Liquor, Price_NZD_700ml FROM alcohol_inventory")
            alcohol_rows = [dict(row) for row in cur.fetchall()]

            cur.execute("SELECT Cocktail_Name, Ingredients, Base_spirit_1, Base_spirit_2 FROM cocktail_notes")
            cocktail_rows = [dict(row) for row in cur.fetchall()]

            cur.execute("SELECT date, cocktail_name FROM tasting_log")
            tasting_rows = [dict(row) for row in cur.fetchall()]

    priced_bottles = []
    brand_price_values: Dict[str, list] = {}
    spirit_groups: Dict[str, list] = {}
    for row in alcohol_rows:
        price = parse_price_nzd(row.get("Price_NZD_700ml"))
        if price is None:
            continue

        brand = str(row.get("Brand") or "").strip()
        base_liquor = str(row.get("Base_Liquor") or "Unknown").strip() or "Unknown"

        priced_bottles.append({"brand": brand or "Unknown", "base_liquor": base_liquor, "price_nzd": price})

        if brand:
            brand_price_values.setdefault(brand, []).append(price)
        spirit_groups.setdefault(base_liquor, []).append(price)

    brand_avg_price = {brand: (sum(values) / len(values)) for brand, values in brand_price_values.items()}
    spirit_avg_price = {spirit: (sum(values) / len(values)) for spirit, values in spirit_groups.items()}

    def cocktail_estimated_cost(row: Dict[str, Any]) -> Any:
        b1 = str(row.get("Brand1") or "").strip()
        b2 = str(row.get("Brand2") or "").strip()
        s1 = str(row.get("Base_spirit_1") or "").strip()
        s2 = str(row.get("Base_spirit_2") or "").strip()
        p1 = brand_avg_price.get(b1)
        p2 = brand_avg_price.get(b2)

        if p1 is None and s1:
            p1 = spirit_avg_price.get(s1)
        if p2 is None and s2:
            p2 = spirit_avg_price.get(s2)

        if p1 is not None and p2 is not None:
            return (p1 * (30.0 / 700.0)) + (p2 * (30.0 / 700.0))
        if p1 is not None:
            return p1 * (60.0 / 700.0)
        if p2 is not None:
            return p2 * (60.0 / 700.0)
        return None

    cocktail_cost_map: Dict[str, Any] = {}
    cocktail_cost_values = []
    for row in cocktail_rows:
        estimated = cocktail_estimated_cost(row)
        name = str(row.get("Cocktail_Name") or "").strip()
        if name and estimated is not None:
            cocktail_cost_map[name] = estimated
            cocktail_cost_values.append(estimated)

    monthly_costs: Dict[str, Dict[str, Any]] = {}
    for row in tasting_rows:
        date_value = str(row.get("date") or "")
        name = str(row.get("cocktail_name") or "").strip()
        if len(date_value) < 7:
            continue
        month = date_value[:7]
        est = cocktail_cost_map.get(name)
        if est is None:
            continue

        if month not in monthly_costs:
            monthly_costs[month] = {"month": month, "total_estimated_cost_nzd": 0.0, "entries": 0}
        monthly_costs[month]["total_estimated_cost_nzd"] += est
        monthly_costs[month]["entries"] += 1

    top_expensive = sorted(priced_bottles, key=lambda item: item["price_nzd"], reverse=True)[:8]
    spirit_avg = [
        {
            "base_spirit": spirit,
            "avg_price_nzd": round2(sum(values) / len(values)),
            "count": len(values),
        }
        for spirit, values in spirit_groups.items()
    ]
    spirit_avg.sort(key=lambda item: item["avg_price_nzd"] or 0, reverse=True)

    monthly_cost_list = list(monthly_costs.values())
    monthly_cost_list.sort(key=lambda item: item["month"])

    cocktail_estimated_costs = [
        {"cocktail_name": name, "estimated_cost_nzd": round2(value)}
        for name, value in cocktail_cost_map.items()
    ]
    cocktail_estimated_costs.sort(key=lambda item: item["cocktail_name"])

    return {
        "avg_bottle_price_nzd": round2(sum(item["price_nzd"] for item in priced_bottles) / len(priced_bottles)) if priced_bottles else None,
        "estimated_cost_per_serving_nzd_avg": round2(sum(cocktail_cost_values) / len(cocktail_cost_values)) if cocktail_cost_values else None,
        "top_expensive_bottles": [
            {
                "brand": item["brand"],
                "base_liquor": item["base_liquor"],
                "price_nzd": round2(item["price_nzd"]),
            }
            for item in top_expensive
        ],
        "base_spirit_avg_price": spirit_avg[:8],
        "tasting_monthly_estimated_cost": [
            {
                "month": item["month"],
                "total_estimated_cost_nzd": round2(item["total_estimated_cost_nzd"]),
                "entries": item["entries"],
            }
            for item in monthly_cost_list[-12:]
        ],
        "cocktail_estimated_costs": cocktail_estimated_costs,
    }


@app.get("/analytics/tasting-insights")
def analytics_tasting_insights() -> Dict[str, Any]:
    dimensions = ["sweetness", "sourness", "bitterness", "booziness", "body", "aroma", "balance", "finish"]

    if USE_SUPABASE:
        tasting_rows = _pg_fetch_all(
            """
            SELECT
                date,
                cocktail_name,
                COALESCE(rating, '') AS rating,
                COALESCE(mood, '') AS mood,
                COALESCE(would_make_again, '') AS would_make_again,
                COALESCE(sweetness, '') AS sweetness,
                COALESCE(sourness, '') AS sourness,
                COALESCE(bitterness, '') AS bitterness,
                COALESCE(booziness, '') AS booziness,
                COALESCE(body, '') AS body,
                COALESCE(aroma, '') AS aroma,
                COALESCE(balance, '') AS balance,
                COALESCE(finish, '') AS finish
            FROM tasting_log
            """
        )
        cocktail_rows = _pg_fetch_all(
            f"SELECT {_pg_columns(['Cocktail_Name'])}, COALESCE({_quote_pg('Base_spirit_1')}, '') AS {_quote_pg('Base_spirit_1')} FROM cocktail_notes"
        )
    else:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    date,
                    cocktail_name,
                    COALESCE(rating, '') AS rating,
                    COALESCE(mood, '') AS mood,
                    COALESCE(would_make_again, '') AS would_make_again,
                    COALESCE(sweetness, '') AS sweetness,
                    COALESCE(sourness, '') AS sourness,
                    COALESCE(bitterness, '') AS bitterness,
                    COALESCE(booziness, '') AS booziness,
                    COALESCE(body, '') AS body,
                    COALESCE(aroma, '') AS aroma,
                    COALESCE(balance, '') AS balance,
                    COALESCE(finish, '') AS finish
                FROM tasting_log
                """
            )
            tasting_rows = [dict(row) for row in cur.fetchall()]

            cur.execute("SELECT Cocktail_Name, COALESCE(Base_spirit_1, '') AS Base_spirit_1 FROM cocktail_notes")
            cocktail_rows = [dict(row) for row in cur.fetchall()]

    cocktail_to_spirit = {
        str(row.get("Cocktail_Name") or "").strip(): str(row.get("Base_spirit_1") or "").strip() or "Unknown"
        for row in cocktail_rows
    }

    ratings = []
    monthly_map: Dict[str, Dict[str, Any]] = {}
    cocktail_rollup: Dict[str, Dict[str, Any]] = {}
    mood_map: Dict[str, int] = {}
    spirit_rollup: Dict[str, Dict[str, Any]] = {}
    make_again_yes = 0
    make_again_known = 0

    flavor_values: Dict[str, list] = {dimension: [] for dimension in dimensions}

    for row in tasting_rows:
        rating_value = parse_float(row.get("rating"))
        cocktail_name = str(row.get("cocktail_name") or "").strip() or "Unknown"
        month = str(row.get("date") or "")[:7]

        if rating_value is not None:
            ratings.append(rating_value)

        if month:
            monthly = monthly_map.setdefault(month, {"month": month, "entries": 0, "ratings": []})
            monthly["entries"] += 1
            if rating_value is not None:
                monthly["ratings"].append(rating_value)

        by_cocktail = cocktail_rollup.setdefault(cocktail_name, {"name": cocktail_name, "entries": 0, "ratings": []})
        by_cocktail["entries"] += 1
        if rating_value is not None:
            by_cocktail["ratings"].append(rating_value)

        mood = str(row.get("mood") or "").strip()
        if mood:
            mood_map[mood] = mood_map.get(mood, 0) + 1

        make_again = str(row.get("would_make_again") or "").strip().lower()
        if make_again in {"yes", "no"}:
            make_again_known += 1
            if make_again == "yes":
                make_again_yes += 1

        spirit = cocktail_to_spirit.get(cocktail_name, "Unknown")
        spirit_entry = spirit_rollup.setdefault(spirit, {"base_spirit": spirit, "entries": 0, "ratings": []})
        spirit_entry["entries"] += 1
        if rating_value is not None:
            spirit_entry["ratings"].append(rating_value)

        for dimension in dimensions:
            dimension_value = parse_float(row.get(dimension))
            if dimension_value is not None:
                flavor_values[dimension].append(dimension_value)

    top_cocktails = []
    for item in cocktail_rollup.values():
        item_ratings = item["ratings"]
        top_cocktails.append(
            {
                "name": item["name"],
                "entries": item["entries"],
                "avg_rating": round2(sum(item_ratings) / len(item_ratings)) if item_ratings else None,
            }
        )
    top_cocktails.sort(key=lambda item: (item["entries"], item["avg_rating"] or 0), reverse=True)

    mood_breakdown = [{"mood": mood, "count": count} for mood, count in mood_map.items()]
    mood_breakdown.sort(key=lambda item: item["count"], reverse=True)

    flavor_profile_avg = []
    for dimension in dimensions:
        values = flavor_values[dimension]
        flavor_profile_avg.append(
            {
                "dimension": dimension,
                "avg": round2(sum(values) / len(values)) if values else None,
            }
        )

    rating_by_base_spirit = []
    for item in spirit_rollup.values():
        item_ratings = item["ratings"]
        rating_by_base_spirit.append(
            {
                "base_spirit": item["base_spirit"],
                "entries": item["entries"],
                "avg_rating": round2(sum(item_ratings) / len(item_ratings)) if item_ratings else None,
            }
        )
    rating_by_base_spirit.sort(key=lambda item: item["entries"], reverse=True)

    monthly_activity = []
    for item in sorted(monthly_map.values(), key=lambda v: v["month"]):
        row_ratings = item["ratings"]
        monthly_activity.append(
            {
                "month": item["month"],
                "entries": item["entries"],
                "avg_rating": round2(sum(row_ratings) / len(row_ratings)) if row_ratings else None,
            }
        )

    return {
        "entries": len(tasting_rows),
        "avg_rating": round2(sum(ratings) / len(ratings)) if ratings else None,
        "would_make_again_rate_pct": round2((make_again_yes * 100.0) / make_again_known) if make_again_known else None,
        "top_cocktails": top_cocktails[:8],
        "mood_breakdown": mood_breakdown[:8],
        "flavor_profile_avg": flavor_profile_avg,
        "rating_by_base_spirit": rating_by_base_spirit[:8],
        "monthly_activity": monthly_activity[-12:],
    }


@app.get("/alcohol")
def list_alcohol(limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    if USE_SUPABASE:
        query = f"SELECT id AS _rowid, {_pg_columns(ALCOHOL_COLUMNS)} FROM alcohol_inventory ORDER BY {_quote_pg('Brand')} LIMIT %s OFFSET %s"
        rows = _pg_fetch_all(query, (limit, offset))
        return {"items": [_resolve_image_paths_in_row(row) for row in rows], "limit": limit, "offset": offset}

    query = "SELECT rowid AS _rowid, * FROM alcohol_inventory ORDER BY Brand LIMIT ? OFFSET ?"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, (limit, offset))
        rows = [dict(row) for row in cur.fetchall()]
    return {"items": rows, "limit": limit, "offset": offset}


@app.post("/alcohol")
def create_alcohol(payload: AlcoholWriteRequest) -> Dict[str, Any]:
    data = payload.dict()
    if not data.get("Brand", "").strip():
        raise HTTPException(status_code=400, detail="Brand is required")

    if USE_SUPABASE:
        row_id = _next_pg_id("alcohol_inventory")
        data["image_path"] = _normalize_image_key(data.get("image_path", ""))

        cols = ALCOHOL_COLUMNS
        query = (
            f"INSERT INTO alcohol_inventory (id, {_pg_columns(cols)}) "
            f"VALUES (%s, {', '.join(['%s'] * len(cols))})"
        )
        _pg_execute(query, tuple([row_id] + [data[col] for col in cols]))

        def _mirror_insert() -> None:
            _mirror_upsert_alcohol_by_brand("", data)

        _mirror_local("create_alcohol", _mirror_insert)

        row = _pg_fetch_one(
            f"SELECT id AS _rowid, {_pg_columns(ALCOHOL_COLUMNS)} FROM alcohol_inventory WHERE id = %s",
            (row_id,),
        )
        return {"item": _resolve_image_paths_in_row(row or {})}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO alcohol_inventory (
                Brand, Base_Liquor, Type, ABV, Country,
                Price_NZD_700ml, Taste, Substitute, Availability, image_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["Brand"],
                data["Base_Liquor"],
                data["Type"],
                data["ABV"],
                data["Country"],
                data["Price_NZD_700ml"],
                data["Taste"],
                data["Substitute"],
                data["Availability"],
                data["image_path"],
            ),
        )
        row_id = cur.lastrowid
        conn.commit()

        cur.execute("SELECT rowid AS _rowid, * FROM alcohol_inventory WHERE rowid = ?", (row_id,))
        row = cur.fetchone()

    return {"item": dict(row)}


@app.put("/alcohol/id/{row_id}")
def update_alcohol(row_id: int, payload: AlcoholWriteRequest) -> Dict[str, Any]:
    data = payload.dict()
    if not data.get("Brand", "").strip():
        raise HTTPException(status_code=400, detail="Brand is required")

    if USE_SUPABASE:
        previous_row = _pg_fetch_one(
            f"SELECT {_quote_pg('Brand')} FROM alcohol_inventory WHERE id = %s",
            (row_id,),
        )
        if not previous_row:
            raise HTTPException(status_code=404, detail="Alcohol row not found")

        data["image_path"] = _normalize_image_key(data.get("image_path", ""))
        assignment = ", ".join(f"{_quote_pg(col)} = %s" for col in ALCOHOL_COLUMNS)
        rowcount = _pg_execute(
            f"UPDATE alcohol_inventory SET {assignment} WHERE id = %s",
            tuple([data[col] for col in ALCOHOL_COLUMNS] + [row_id]),
        )
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Alcohol row not found")

        def _mirror_update() -> None:
            _mirror_upsert_alcohol_by_brand(str(previous_row.get("Brand") or ""), data)

        _mirror_local("update_alcohol", _mirror_update)

        row = _pg_fetch_one(
            f"SELECT id AS _rowid, {_pg_columns(ALCOHOL_COLUMNS)} FROM alcohol_inventory WHERE id = %s",
            (row_id,),
        )
        return {"item": _resolve_image_paths_in_row(row or {})}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE alcohol_inventory
            SET Brand = ?, Base_Liquor = ?, Type = ?, ABV = ?, Country = ?,
                Price_NZD_700ml = ?, Taste = ?, Substitute = ?, Availability = ?, image_path = ?
            WHERE rowid = ?
            """,
            (
                data["Brand"],
                data["Base_Liquor"],
                data["Type"],
                data["ABV"],
                data["Country"],
                data["Price_NZD_700ml"],
                data["Taste"],
                data["Substitute"],
                data["Availability"],
                data["image_path"],
                row_id,
            ),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alcohol row not found")
        conn.commit()

        cur.execute("SELECT rowid AS _rowid, * FROM alcohol_inventory WHERE rowid = ?", (row_id,))
        row = cur.fetchone()

    return {"item": dict(row)}


@app.delete("/alcohol/id/{row_id}")
def delete_alcohol(row_id: int) -> Dict[str, str]:
    if USE_SUPABASE:
        previous_row = _pg_fetch_one(
            f"SELECT {_quote_pg('Brand')} FROM alcohol_inventory WHERE id = %s",
            (row_id,),
        )
        if not previous_row:
            raise HTTPException(status_code=404, detail="Alcohol row not found")

        rowcount = _pg_execute("DELETE FROM alcohol_inventory WHERE id = %s", (row_id,))
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Alcohol row not found")

        def _mirror_delete() -> None:
            _mirror_delete_alcohol_by_brand(str(previous_row.get("Brand") or ""))

        _mirror_local("delete_alcohol", _mirror_delete)
        return {"status": "deleted"}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM alcohol_inventory WHERE rowid = ?", (row_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alcohol row not found")
        conn.commit()

    return {"status": "deleted"}


@app.get("/tags", response_model=TagListResponse)
def list_tags(
    entity_type: str = Query("", description="Optional entity type filter"),
    entity_rowid: int = Query(0, ge=0, description="Optional entity rowid filter"),
) -> TagListResponse:
    if USE_SUPABASE:
        clauses = []
        params: List[Any] = []
        if entity_type:
            clauses.append("entity_type = %s")
            params.append(entity_type)
        if entity_rowid:
            clauses.append("entity_rowid = %s")
            params.append(entity_rowid)
        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = _pg_fetch_all(
            f"SELECT id, entity_type, entity_rowid, tag, created_at FROM tags {where_clause} ORDER BY created_at DESC",
            tuple(params),
        )
        items = [TagItem(**row) for row in rows]
        return TagListResponse(items=items)

    clauses = []
    params = []
    if entity_type:
        clauses.append("entity_type = ?")
        params.append(entity_type)
    if entity_rowid:
        clauses.append("entity_rowid = ?")
        params.append(entity_rowid)

    where_clause = ""
    if clauses:
        where_clause = "WHERE " + " AND ".join(clauses)

    query = f"""
        SELECT id, entity_type, entity_rowid, tag, created_at
        FROM tags
        {where_clause}
        ORDER BY created_at DESC
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        rows = [dict(row) for row in cur.fetchall()]

    items = [TagItem(**row) for row in rows]
    return TagListResponse(items=items)


@app.post("/tags", response_model=TagItem)
def create_tag(payload: TagCreateRequest) -> TagItem:
    entity_type = payload.entity_type.strip().lower()
    if entity_type not in ("alcohol", "cocktail"):
        raise HTTPException(status_code=400, detail="entity_type must be 'alcohol' or 'cocktail'")

    tag_value = payload.tag.strip()
    if not tag_value:
        raise HTTPException(status_code=400, detail="tag is required")

    item = {
        "id": str(uuid.uuid4()),
        "entity_type": entity_type,
        "entity_rowid": payload.entity_rowid,
        "tag": tag_value,
        "created_at": _now_local_iso(),
    }

    if USE_SUPABASE:
        _pg_execute(
            "INSERT INTO tags (id, entity_type, entity_rowid, tag, created_at) VALUES (%s, %s, %s, %s, %s)",
            (item["id"], item["entity_type"], item["entity_rowid"], item["tag"], item["created_at"]),
        )

        def _mirror_create_tag() -> None:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO tags (id, entity_type, entity_rowid, tag, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (item["id"], item["entity_type"], item["entity_rowid"], item["tag"], item["created_at"]),
                )
                conn.commit()

        _mirror_local("create_tag", _mirror_create_tag)
        return TagItem(**item)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tags (id, entity_type, entity_rowid, tag, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (item["id"], item["entity_type"], item["entity_rowid"], item["tag"], item["created_at"]),
        )
        conn.commit()

    return TagItem(**item)


@app.delete("/tags/{tag_id}")
def delete_tag(tag_id: str) -> Dict[str, str]:
    if USE_SUPABASE:
        rowcount = _pg_execute("DELETE FROM tags WHERE id = %s", (tag_id,))
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Tag not found")

        def _mirror_delete_tag() -> None:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
                conn.commit()

        _mirror_local("delete_tag", _mirror_delete_tag)
        return {"status": "deleted"}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tag not found")
        conn.commit()

    return {"status": "deleted"}


@app.get("/saved-views", response_model=SavedViewListResponse)
def list_saved_views() -> SavedViewListResponse:
    if USE_SUPABASE:
        rows = _pg_fetch_all(
            """
            SELECT id, name, payload_json, created_at
            FROM saved_views
            ORDER BY created_at DESC
            """
        )
        items = []
        for row in rows:
            payload_json = row.get("payload_json") if row.get("payload_json") else "{}"
            items.append(
                SavedViewItem(
                    id=str(row.get("id") or ""),
                    name=str(row.get("name") or ""),
                    payload=json.loads(payload_json),
                    created_at=str(row.get("created_at") or ""),
                )
            )
        return SavedViewListResponse(items=items)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, payload_json, created_at
            FROM saved_views
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()

    items = []
    for row in rows:
        payload_json = row["payload_json"] if row["payload_json"] else "{}"
        items.append(
            SavedViewItem(
                id=row["id"],
                name=row["name"],
                payload=json.loads(payload_json),
                created_at=row["created_at"],
            )
        )

    return SavedViewListResponse(items=items)


@app.post("/saved-views", response_model=SavedViewItem)
def create_saved_view(payload: SavedViewCreateRequest) -> SavedViewItem:
    view_id = str(uuid.uuid4())
    created_at = _now_local_iso()

    if USE_SUPABASE:
        _pg_execute(
            "INSERT INTO saved_views (id, name, payload_json, created_at) VALUES (%s, %s, %s, %s)",
            (view_id, payload.name.strip(), json.dumps(payload.payload), created_at),
        )

        def _mirror_create_saved_view() -> None:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO saved_views (id, name, payload_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (view_id, payload.name.strip(), json.dumps(payload.payload), created_at),
                )
                conn.commit()

        _mirror_local("create_saved_view", _mirror_create_saved_view)
        return SavedViewItem(id=view_id, name=payload.name.strip(), payload=payload.payload, created_at=created_at)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO saved_views (id, name, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (view_id, payload.name.strip(), json.dumps(payload.payload), created_at),
        )
        conn.commit()

    return SavedViewItem(id=view_id, name=payload.name.strip(), payload=payload.payload, created_at=created_at)


@app.delete("/saved-views/{view_id}")
def delete_saved_view(view_id: str) -> Dict[str, str]:
    if USE_SUPABASE:
        rowcount = _pg_execute("DELETE FROM saved_views WHERE id = %s", (view_id,))
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Saved view not found")

        def _mirror_delete_saved_view() -> None:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM saved_views WHERE id = ?", (view_id,))
                conn.commit()

        _mirror_local("delete_saved_view", _mirror_delete_saved_view)
        return {"status": "deleted"}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM saved_views WHERE id = ?", (view_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Saved view not found")
        conn.commit()

    return {"status": "deleted"}


@app.get("/cocktails")
def list_cocktails(limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    if USE_SUPABASE:
        query = f"SELECT id AS _rowid, {_pg_columns(COCKTAIL_COLUMNS)} FROM cocktail_notes ORDER BY {_quote_pg('Cocktail_Name')} LIMIT %s OFFSET %s"
        rows = _pg_fetch_all(query, (limit, offset))
        return {"items": [_resolve_image_paths_in_row(row) for row in rows], "limit": limit, "offset": offset}

    query = "SELECT rowid AS _rowid, * FROM cocktail_notes ORDER BY Cocktail_Name LIMIT ? OFFSET ?"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, (limit, offset))
        rows = [dict(row) for row in cur.fetchall()]
    return {"items": rows, "limit": limit, "offset": offset}


@app.post("/cocktails")
def create_cocktail(payload: CocktailWriteRequest) -> Dict[str, Any]:
    data = payload.dict()
    if not data.get("Cocktail_Name", "").strip():
        raise HTTPException(status_code=400, detail="Cocktail_Name is required")

    if USE_SUPABASE:
        row_id = _next_pg_id("cocktail_notes")
        data["image_path"] = _normalize_image_key(data.get("image_path", ""))
        cols = COCKTAIL_COLUMNS
        query = (
            f"INSERT INTO cocktail_notes (id, {_pg_columns(cols)}) "
            f"VALUES (%s, {', '.join(['%s'] * len(cols))})"
        )
        _pg_execute(query, tuple([row_id] + [data[col] for col in cols]))

        def _mirror_insert_cocktail() -> None:
            _mirror_upsert_cocktail_by_name("", data)

        _mirror_local("create_cocktail", _mirror_insert_cocktail)

        row = _pg_fetch_one(
            f"SELECT id AS _rowid, {_pg_columns(COCKTAIL_COLUMNS)} FROM cocktail_notes WHERE id = %s",
            (row_id,),
        )
        return {"item": _resolve_image_paths_in_row(row or {})}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO cocktail_notes (
                Cocktail_Name, Ingredients, Rating_Jason, Rating_Jaime, Rating_overall,
                Base_spirit_1, Type1, Brand1, Base_spirit_2, Type2, Brand2,
                Citrus, Garnish, Notes, DatetimeAdded, Prep_Time, Difficulty, image_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["Cocktail_Name"],
                data["Ingredients"],
                data["Rating_Jason"],
                data["Rating_Jaime"],
                data["Rating_overall"],
                data["Base_spirit_1"],
                data["Type1"],
                data["Brand1"],
                data["Base_spirit_2"],
                data["Type2"],
                data["Brand2"],
                data["Citrus"],
                data["Garnish"],
                data["Notes"],
                data["DatetimeAdded"],
                data["Prep_Time"],
                data["Difficulty"],
                data["image_path"],
            ),
        )
        row_id = cur.lastrowid
        conn.commit()

        cur.execute("SELECT rowid AS _rowid, * FROM cocktail_notes WHERE rowid = ?", (row_id,))
        row = cur.fetchone()

    return {"item": dict(row)}


@app.put("/cocktails/id/{row_id}")
def update_cocktail(row_id: int, payload: CocktailWriteRequest) -> Dict[str, Any]:
    data = payload.dict()
    if not data.get("Cocktail_Name", "").strip():
        raise HTTPException(status_code=400, detail="Cocktail_Name is required")

    if USE_SUPABASE:
        previous_row = _pg_fetch_one(
            f"SELECT {_quote_pg('Cocktail_Name')} FROM cocktail_notes WHERE id = %s",
            (row_id,),
        )
        if not previous_row:
            raise HTTPException(status_code=404, detail="Cocktail row not found")

        data["image_path"] = _normalize_image_key(data.get("image_path", ""))
        assignment = ", ".join(f"{_quote_pg(col)} = %s" for col in COCKTAIL_COLUMNS)
        rowcount = _pg_execute(
            f"UPDATE cocktail_notes SET {assignment} WHERE id = %s",
            tuple([data[col] for col in COCKTAIL_COLUMNS] + [row_id]),
        )
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Cocktail row not found")

        def _mirror_update_cocktail() -> None:
            _mirror_upsert_cocktail_by_name(str(previous_row.get("Cocktail_Name") or ""), data)

        _mirror_local("update_cocktail", _mirror_update_cocktail)

        row = _pg_fetch_one(
            f"SELECT id AS _rowid, {_pg_columns(COCKTAIL_COLUMNS)} FROM cocktail_notes WHERE id = %s",
            (row_id,),
        )
        return {"item": _resolve_image_paths_in_row(row or {})}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE cocktail_notes
            SET Cocktail_Name = ?, Ingredients = ?, Rating_Jason = ?, Rating_Jaime = ?, Rating_overall = ?,
                Base_spirit_1 = ?, Type1 = ?, Brand1 = ?, Base_spirit_2 = ?, Type2 = ?, Brand2 = ?,
                Citrus = ?, Garnish = ?, Notes = ?, DatetimeAdded = ?, Prep_Time = ?, Difficulty = ?, image_path = ?
            WHERE rowid = ?
            """,
            (
                data["Cocktail_Name"],
                data["Ingredients"],
                data["Rating_Jason"],
                data["Rating_Jaime"],
                data["Rating_overall"],
                data["Base_spirit_1"],
                data["Type1"],
                data["Brand1"],
                data["Base_spirit_2"],
                data["Type2"],
                data["Brand2"],
                data["Citrus"],
                data["Garnish"],
                data["Notes"],
                data["DatetimeAdded"],
                data["Prep_Time"],
                data["Difficulty"],
                data["image_path"],
                row_id,
            ),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Cocktail row not found")
        conn.commit()

        cur.execute("SELECT rowid AS _rowid, * FROM cocktail_notes WHERE rowid = ?", (row_id,))
        row = cur.fetchone()

    return {"item": dict(row)}


@app.delete("/cocktails/id/{row_id}")
def delete_cocktail(row_id: int) -> Dict[str, str]:
    if USE_SUPABASE:
        previous_row = _pg_fetch_one(
            f"SELECT {_quote_pg('Cocktail_Name')} FROM cocktail_notes WHERE id = %s",
            (row_id,),
        )
        if not previous_row:
            raise HTTPException(status_code=404, detail="Cocktail row not found")

        rowcount = _pg_execute("DELETE FROM cocktail_notes WHERE id = %s", (row_id,))
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Cocktail row not found")

        def _mirror_delete_cocktail() -> None:
            _mirror_delete_cocktail_by_name(str(previous_row.get("Cocktail_Name") or ""))

        _mirror_local("delete_cocktail", _mirror_delete_cocktail)
        return {"status": "deleted"}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM cocktail_notes WHERE rowid = ?", (row_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Cocktail row not found")
        conn.commit()

    return {"status": "deleted"}


@app.get("/alcohol/{brand}")
def get_alcohol(brand: str) -> Dict[str, Any]:
    if USE_SUPABASE:
        row = _pg_fetch_one(
            f"SELECT {_pg_columns(ALCOHOL_COLUMNS)} FROM alcohol_inventory WHERE {_quote_pg('Brand')} = %s",
            (brand,),
        )
        if not row:
            raise HTTPException(status_code=404, detail="Alcohol not found")
        return {"item": _resolve_image_paths_in_row(row)}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM alcohol_inventory WHERE Brand = ?", (brand,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Alcohol not found")
    return {"item": dict(row)}


@app.get("/cocktails/{name}")
def get_cocktail(name: str) -> Dict[str, Any]:
    if USE_SUPABASE:
        row = _pg_fetch_one(
            f"SELECT {_pg_columns(COCKTAIL_COLUMNS)} FROM cocktail_notes WHERE {_quote_pg('Cocktail_Name')} = %s",
            (name,),
        )
        if not row:
            raise HTTPException(status_code=404, detail="Cocktail not found")
        return {"item": _resolve_image_paths_in_row(row)}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cocktail_notes WHERE Cocktail_Name = ?", (name,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Cocktail not found")
    return {"item": dict(row)}


@app.post("/ai/twist-suggestions", response_model=TwistResponse)
def ai_twist_suggestions(payload: TwistRequest) -> TwistResponse:
    provider = (payload.provider or "local").lower().strip()

    if provider in ("groq", "openai"):
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            return TwistResponse(
                provider="groq",
                suggestions=[TwistSuggestion(**item) for item in build_local_twist_suggestions(payload)],
                note="GROQ_API_KEY is not configured. Returned local fallback suggestions."
            )

        try:
            ai_result = call_groq_twist_suggestions(payload, api_key)
            return TwistResponse(
                provider="groq",
                suggestions=[TwistSuggestion(**item) for item in ai_result["suggestions"]],
                note=f"Generated by Groq model {ai_result['model']}."
            )
        except Exception as exc:
            return TwistResponse(
                provider="groq",
                suggestions=[TwistSuggestion(**item) for item in build_local_twist_suggestions(payload)],
                note=f"Groq request failed ({exc}). Returned local fallback suggestions."
            )

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return TwistResponse(
                provider="gemini",
                suggestions=[TwistSuggestion(**item) for item in build_local_twist_suggestions(payload)],
                note="GEMINI_API_KEY is not configured. Returned local fallback suggestions."
            )

        try:
            ai_result = call_gemini_twist_suggestions(payload, api_key)
            return TwistResponse(
                provider="gemini",
                suggestions=[TwistSuggestion(**item) for item in ai_result["suggestions"]],
                note=f"Generated by Gemini model {ai_result['model']}."
            )
        except Exception as exc:
            return TwistResponse(
                provider="gemini",
                suggestions=[TwistSuggestion(**item) for item in build_local_twist_suggestions(payload)],
                note=f"Gemini request failed ({exc}). Returned local fallback suggestions."
            )

    return TwistResponse(
        provider="local",
        suggestions=[TwistSuggestion(**item) for item in build_local_twist_suggestions(payload)],
        note="Generated with local rules-based fallback engine."
    )


@app.get("/tasting-logs", response_model=TastingLogListResponse)
def list_tasting_logs() -> TastingLogListResponse:
    if USE_SUPABASE:
        rows = _pg_fetch_all(
            """
            SELECT id, date, cocktail_name, COALESCE(rating, '') AS rating,
                   COALESCE(notes, '') AS notes,
                   COALESCE(mood, '') AS mood,
                   COALESCE(occasion, '') AS occasion,
                   COALESCE(location, '') AS location,
                   COALESCE(would_make_again, '') AS would_make_again,
                   COALESCE(change_next_time, '') AS change_next_time,
                   COALESCE(sweetness, '') AS sweetness,
                   COALESCE(sourness, '') AS sourness,
                   COALESCE(bitterness, '') AS bitterness,
                   COALESCE(booziness, '') AS booziness,
                   COALESCE(body, '') AS body,
                   COALESCE(aroma, '') AS aroma,
                   COALESCE(balance, '') AS balance,
                   COALESCE(finish, '') AS finish,
                   created_at
            FROM tasting_log
            ORDER BY date DESC, created_at DESC
            """
        )
        items = [TastingLogItem(**row) for row in rows]
        return TastingLogListResponse(items=items)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, date, cocktail_name, COALESCE(rating, '') AS rating,
                   COALESCE(notes, '') AS notes,
                   COALESCE(mood, '') AS mood,
                   COALESCE(occasion, '') AS occasion,
                   COALESCE(location, '') AS location,
                   COALESCE(would_make_again, '') AS would_make_again,
                   COALESCE(change_next_time, '') AS change_next_time,
                   COALESCE(sweetness, '') AS sweetness,
                   COALESCE(sourness, '') AS sourness,
                   COALESCE(bitterness, '') AS bitterness,
                   COALESCE(booziness, '') AS booziness,
                   COALESCE(body, '') AS body,
                   COALESCE(aroma, '') AS aroma,
                   COALESCE(balance, '') AS balance,
                   COALESCE(finish, '') AS finish,
                   created_at
            FROM tasting_log
            ORDER BY date DESC, created_at DESC
            """
        )
        rows = [dict(row) for row in cur.fetchall()]

    items = [TastingLogItem(**row) for row in rows]
    return TastingLogListResponse(items=items)


@app.post("/tasting-logs", response_model=TastingLogItem)
def create_tasting_log(payload: TastingLogCreateRequest) -> TastingLogItem:
    date_value = (payload.date or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_value):
        now_time = datetime.now().strftime("%H:%M:%S")
        date_value = f"{date_value}T{now_time}"
    elif not date_value:
        date_value = _now_local_iso()

    item = {
        "id": str(uuid.uuid4()),
        "date": date_value,
        "cocktail_name": payload.cocktail_name,
        "rating": payload.rating,
        "notes": payload.notes,
        "mood": payload.mood,
        "occasion": payload.occasion,
        "location": payload.location,
        "would_make_again": payload.would_make_again,
        "change_next_time": payload.change_next_time,
        "sweetness": payload.sweetness,
        "sourness": payload.sourness,
        "bitterness": payload.bitterness,
        "booziness": payload.booziness,
        "body": payload.body,
        "aroma": payload.aroma,
        "balance": payload.balance,
        "finish": payload.finish,
        "created_at": _now_local_iso(),
    }

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tasting_log (
                id, date, cocktail_name, rating, notes,
                mood, occasion, location, would_make_again, change_next_time,
                sweetness, sourness, bitterness, booziness,
                body, aroma, balance, finish,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["date"],
                item["cocktail_name"],
                item["rating"],
                item["notes"],
                item["mood"],
                item["occasion"],
                item["location"],
                item["would_make_again"],
                item["change_next_time"],
                item["sweetness"],
                item["sourness"],
                item["bitterness"],
                item["booziness"],
                item["body"],
                item["aroma"],
                item["balance"],
                item["finish"],
                item["created_at"],
            ),
        )
        conn.commit()

    return TastingLogItem(**item)


@app.delete("/tasting-logs/{item_id}")
def delete_tasting_log(item_id: str) -> Dict[str, str]:
    if USE_SUPABASE:
        rowcount = _pg_execute("DELETE FROM tasting_log WHERE id = %s", (item_id,))
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Tasting log not found")

        def _mirror_delete_tasting() -> None:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM tasting_log WHERE id = ?", (item_id,))
                conn.commit()

        _mirror_local("delete_tasting_log", _mirror_delete_tasting)
        return {"status": "deleted"}

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM tasting_log WHERE id = ?", (item_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tasting log not found")
        conn.commit()

    return {"status": "deleted"}
