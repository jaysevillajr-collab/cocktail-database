from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

import psycopg
import requests
from psycopg.rows import dict_row


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


def normalize_image_key(path_value: str) -> str:
    value = str(path_value or "").strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    if value.lower().startswith("images/"):
        value = value[7:]
    return value.strip("/")


def quote_pg(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'


def fetch_all_pg(conn: psycopg.Connection[Any], query: str, params: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def ensure_local_tables(conn: sqlite3.Connection) -> None:
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
            mood TEXT,
            occasion TEXT,
            location TEXT,
            would_make_again TEXT,
            change_next_time TEXT,
            sweetness TEXT,
            sourness TEXT,
            bitterness TEXT,
            booziness TEXT,
            body TEXT,
            aroma TEXT,
            balance TEXT,
            finish TEXT,
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
    conn.commit()


def sync_alcohol(pg_conn: psycopg.Connection[Any], sqlite_conn: sqlite3.Connection) -> Dict[str, int]:
    columns = [
        "Brand", "Base_Liquor", "Type", "ABV", "Country",
        "Price_NZD_700ml", "Taste", "Substitute", "Availability", "image_path",
    ]
    select_sql = f"SELECT {', '.join(quote_pg(c) for c in columns)} FROM alcohol_inventory"
    rows = fetch_all_pg(pg_conn, select_sql)

    cur = sqlite_conn.cursor()
    cur.execute("DELETE FROM alcohol_inventory")

    inserted = 0
    for row in rows:
        values = [str(row.get(col) or "") for col in columns]
        values[-1] = f"images/{normalize_image_key(values[-1])}" if normalize_image_key(values[-1]) else ""
        cur.execute(
            """
            INSERT INTO alcohol_inventory (
                Brand, Base_Liquor, Type, ABV, Country,
                Price_NZD_700ml, Taste, Substitute, Availability, image_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(values),
        )
        inserted += 1

    sqlite_conn.commit()
    return {"inserted": inserted, "deleted": 0}


def sync_cocktails(pg_conn: psycopg.Connection[Any], sqlite_conn: sqlite3.Connection) -> Dict[str, int]:
    columns = [
        "Cocktail_Name", "Ingredients", "Rating_Jason", "Rating_Jaime", "Rating_overall",
        "Base_spirit_1", "Type1", "Brand1", "Base_spirit_2", "Type2", "Brand2",
        "Citrus", "Garnish", "Notes", "DatetimeAdded", "Prep_Time", "Difficulty", "image_path",
    ]
    select_sql = f"SELECT {', '.join(quote_pg(c) for c in columns)} FROM cocktail_notes"
    rows = fetch_all_pg(pg_conn, select_sql)

    cur = sqlite_conn.cursor()
    cur.execute("DELETE FROM cocktail_notes")

    inserted = 0
    for row in rows:
        values = [str(row.get(col) or "") for col in columns]
        values[-1] = f"images/{normalize_image_key(values[-1])}" if normalize_image_key(values[-1]) else ""
        cur.execute(
            """
            INSERT INTO cocktail_notes (
                Cocktail_Name, Ingredients, Rating_Jason, Rating_Jaime, Rating_overall,
                Base_spirit_1, Type1, Brand1, Base_spirit_2, Type2, Brand2,
                Citrus, Garnish, Notes, DatetimeAdded, Prep_Time, Difficulty, image_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(values),
        )
        inserted += 1

    sqlite_conn.commit()
    return {"inserted": inserted, "deleted": 0}


def sync_tasting_log(pg_conn: psycopg.Connection[Any], sqlite_conn: sqlite3.Connection) -> Dict[str, int]:
    columns = [
        "id", "date", "cocktail_name", "rating", "notes", "mood", "occasion", "location",
        "would_make_again", "change_next_time", "sweetness", "sourness", "bitterness",
        "booziness", "body", "aroma", "balance", "finish", "created_at",
    ]
    rows = fetch_all_pg(pg_conn, f"SELECT {', '.join(columns)} FROM tasting_log")

    cur = sqlite_conn.cursor()
    cur.execute("DELETE FROM tasting_log")
    inserted = 0
    for row in rows:
        values = [str(row.get(col) or "") for col in columns]
        cur.execute(
            """
            INSERT INTO tasting_log (
                id, date, cocktail_name, rating, notes, mood, occasion, location,
                would_make_again, change_next_time, sweetness, sourness, bitterness,
                booziness, body, aroma, balance, finish, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(values),
        )
        inserted += 1

    sqlite_conn.commit()
    return {"inserted": inserted, "deleted": 0}


def sync_saved_views(pg_conn: psycopg.Connection[Any], sqlite_conn: sqlite3.Connection) -> Dict[str, int]:
    columns = ["id", "name", "payload_json", "created_at"]
    rows = fetch_all_pg(pg_conn, f"SELECT {', '.join(columns)} FROM saved_views")

    cur = sqlite_conn.cursor()
    cur.execute("DELETE FROM saved_views")
    inserted = 0
    for row in rows:
        values = [str(row.get(col) or "") for col in columns]
        cur.execute(
            "INSERT INTO saved_views (id, name, payload_json, created_at) VALUES (?, ?, ?, ?)",
            tuple(values),
        )
        inserted += 1

    sqlite_conn.commit()
    return {"inserted": inserted, "deleted": 0}


def sync_tags(pg_conn: psycopg.Connection[Any], sqlite_conn: sqlite3.Connection) -> Dict[str, int]:
    columns = ["id", "entity_type", "entity_rowid", "tag", "created_at"]
    rows = fetch_all_pg(pg_conn, f"SELECT {', '.join(columns)} FROM tags")

    cur = sqlite_conn.cursor()
    cur.execute("DELETE FROM tags")
    inserted = 0
    for row in rows:
        values = [str(row.get("id") or ""), str(row.get("entity_type") or ""), int(row.get("entity_rowid") or 0), str(row.get("tag") or ""), str(row.get("created_at") or "")]
        cur.execute(
            "INSERT INTO tags (id, entity_type, entity_rowid, tag, created_at) VALUES (?, ?, ?, ?, ?)",
            tuple(values),
        )
        inserted += 1

    sqlite_conn.commit()
    return {"inserted": inserted, "deleted": 0}


def list_bucket_keys(supabase_url: str, service_role_key: str, bucket: str, prefix: str = "") -> List[str]:
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{supabase_url}/storage/v1/object/list/{bucket}",
        headers=headers,
        json={"prefix": prefix, "limit": 1000, "offset": 0},
        timeout=60,
    )
    response.raise_for_status()

    keys: List[str] = []
    for item in response.json():
        name = str(item.get("name") or "").strip()
        item_id = str(item.get("id") or "").strip()
        if not name:
            continue
        next_key = f"{prefix}/{name}" if prefix else name
        if item_id:
            keys.append(next_key)
        else:
            keys.extend(list_bucket_keys(supabase_url, service_role_key, bucket, next_key))
    return keys


def sync_images(supabase_url: str, service_role_key: str, bucket: str, local_images_path: Path) -> Dict[str, int]:
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }

    keys = list_bucket_keys(supabase_url, service_role_key, bucket)
    downloaded = 0

    for key in keys:
        target_path = local_images_path / key
        target_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"{supabase_url}/storage/v1/object/{bucket}/{key}"
        response = requests.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        target_path.write_bytes(response.content)
        downloaded += 1

    return {"downloaded": downloaded, "keys": len(keys)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Supabase data/images into local SQLite/images mirror")
    parser.add_argument("--skip-images", action="store_true", help="Skip syncing images from Supabase storage")
    parser.add_argument("--local-db", default="", help="Override local SQLite DB path")
    parser.add_argument("--local-images", default="", help="Override local images directory")
    args = parser.parse_args()

    load_env_file()

    supabase_url = str(os.getenv("SUPABASE_URL", "")).strip().rstrip("/")
    service_role_key = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
    supabase_db_url = str(os.getenv("SUPABASE_DB_URL", "")).strip()
    bucket = str(os.getenv("SUPABASE_STORAGE_BUCKET", "images")).strip() or "images"

    local_db_path = Path(args.local_db.strip() or str(os.getenv("COCKTAIL_DB_PATH", "")).strip() or str((Path(__file__).resolve().parents[3] / "cocktail_database.db"))).resolve()
    local_images_path = Path(args.local_images.strip() or str(os.getenv("COCKTAIL_IMAGES_PATH", "")).strip() or str((Path(__file__).resolve().parents[3] / "images"))).resolve()

    if not supabase_url or not service_role_key or not supabase_db_url:
        raise ValueError("SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and SUPABASE_DB_URL must be set")

    local_db_path.parent.mkdir(parents=True, exist_ok=True)
    local_images_path.mkdir(parents=True, exist_ok=True)

    sqlite_conn = sqlite3.connect(local_db_path)
    try:
        ensure_local_tables(sqlite_conn)

        with psycopg.connect(supabase_db_url, prepare_threshold=None, row_factory=dict_row) as pg_conn:
            summary = {
                "alcohol_inventory": sync_alcohol(pg_conn, sqlite_conn),
                "cocktail_notes": sync_cocktails(pg_conn, sqlite_conn),
                "tasting_log": sync_tasting_log(pg_conn, sqlite_conn),
                "saved_views": sync_saved_views(pg_conn, sqlite_conn),
                "tags": sync_tags(pg_conn, sqlite_conn),
            }

        image_summary: Dict[str, Any] = {"downloaded": 0, "keys": 0, "skipped": bool(args.skip_images)}
        if not args.skip_images:
            image_summary = sync_images(supabase_url, service_role_key, bucket, local_images_path)

        print(
            {
                "local_db_path": str(local_db_path),
                "local_images_path": str(local_images_path),
                "tables": summary,
                "images": image_summary,
            }
        )
    finally:
        sqlite_conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
