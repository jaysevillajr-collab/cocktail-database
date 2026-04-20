from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence

import psycopg


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


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_PATH = (REPO_ROOT / "cocktail_database.db").resolve()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS alcohol_inventory (
    id BIGINT PRIMARY KEY,
    "Brand" TEXT NOT NULL DEFAULT '',
    "Base_Liquor" TEXT NOT NULL DEFAULT '',
    "Type" TEXT NOT NULL DEFAULT '',
    "ABV" TEXT NOT NULL DEFAULT '',
    "Country" TEXT NOT NULL DEFAULT '',
    "Price_NZD_700ml" TEXT NOT NULL DEFAULT '',
    "Taste" TEXT NOT NULL DEFAULT '',
    "Substitute" TEXT NOT NULL DEFAULT '',
    "Availability" TEXT NOT NULL DEFAULT '',
    "image_path" TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS cocktail_notes (
    id BIGINT PRIMARY KEY,
    "Cocktail_Name" TEXT NOT NULL DEFAULT '',
    "Ingredients" TEXT NOT NULL DEFAULT '',
    "Rating_Jason" TEXT NOT NULL DEFAULT '',
    "Rating_Jaime" TEXT NOT NULL DEFAULT '',
    "Rating_overall" TEXT NOT NULL DEFAULT '',
    "Base_spirit_1" TEXT NOT NULL DEFAULT '',
    "Type1" TEXT NOT NULL DEFAULT '',
    "Brand1" TEXT NOT NULL DEFAULT '',
    "Base_spirit_2" TEXT NOT NULL DEFAULT '',
    "Type2" TEXT NOT NULL DEFAULT '',
    "Brand2" TEXT NOT NULL DEFAULT '',
    "Citrus" TEXT NOT NULL DEFAULT '',
    "Garnish" TEXT NOT NULL DEFAULT '',
    "Notes" TEXT NOT NULL DEFAULT '',
    "DatetimeAdded" TEXT NOT NULL DEFAULT '',
    "Prep_Time" TEXT NOT NULL DEFAULT '',
    "Difficulty" TEXT NOT NULL DEFAULT '',
    "image_path" TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tasting_log (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    cocktail_name TEXT NOT NULL,
    rating TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    mood TEXT NOT NULL DEFAULT '',
    occasion TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    would_make_again TEXT NOT NULL DEFAULT '',
    change_next_time TEXT NOT NULL DEFAULT '',
    sweetness TEXT NOT NULL DEFAULT '',
    sourness TEXT NOT NULL DEFAULT '',
    bitterness TEXT NOT NULL DEFAULT '',
    booziness TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    aroma TEXT NOT NULL DEFAULT '',
    balance TEXT NOT NULL DEFAULT '',
    finish TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_views (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_rowid BIGINT NOT NULL,
    tag TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alcohol_inventory_brand ON alcohol_inventory ("Brand");
CREATE INDEX IF NOT EXISTS idx_cocktail_notes_name ON cocktail_notes ("Cocktail_Name");
CREATE INDEX IF NOT EXISTS idx_tasting_log_created_at ON tasting_log (created_at);
CREATE INDEX IF NOT EXISTS idx_tags_entity ON tags (entity_type, entity_rowid);
"""


def normalize(value: Any) -> Any:
    if value is None:
        return ""
    return value


def read_sqlite_rows(conn: sqlite3.Connection, query: str, columns: Sequence[str]) -> list[tuple[Any, ...]]:
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    return [tuple(normalize(row[col]) for col in columns) for row in rows]


def upsert_many(pg_conn: psycopg.Connection, sql: str, rows: Iterable[tuple[Any, ...]]) -> int:
    payload = list(rows)
    if not payload:
        return 0
    with pg_conn.cursor() as cur:
        cur.executemany(sql, payload)
    return len(payload)


def count_table_sqlite(conn: sqlite3.Connection, table_name: str) -> int:
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    return int(cur.fetchone()[0])


def count_table_postgres(conn: psycopg.Connection, table_name: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return int(cur.fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Cocktail SQLite data to Supabase Postgres")
    parser.add_argument(
        "--sqlite-path",
        default=os.getenv("COCKTAIL_DB_PATH", str(DEFAULT_SQLITE_PATH)),
        help="Path to source SQLite DB (defaults to COCKTAIL_DB_PATH or repo cocktail_database.db)",
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("SUPABASE_DB_URL", "").strip(),
        help="Supabase Postgres URL (defaults to SUPABASE_DB_URL)",
    )
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite_path).resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    db_url = str(args.db_url or "").strip()
    if not db_url:
        raise ValueError("SUPABASE_DB_URL is required (set env or pass --db-url)")

    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row

    report: dict[str, Any] = {
        "sqlite_path": str(sqlite_path),
        "tables": {},
    }

    try:
        with psycopg.connect(db_url, prepare_threshold=None) as pg_conn:
            pg_conn.autocommit = False
            with pg_conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
            pg_conn.commit()

            alcohol_columns = [
                "id", "Brand", "Base_Liquor", "Type", "ABV", "Country",
                "Price_NZD_700ml", "Taste", "Substitute", "Availability", "image_path",
            ]
            cocktail_columns = [
                "id", "Cocktail_Name", "Ingredients", "Rating_Jason", "Rating_Jaime", "Rating_overall",
                "Base_spirit_1", "Type1", "Brand1", "Base_spirit_2", "Type2", "Brand2",
                "Citrus", "Garnish", "Notes", "DatetimeAdded", "Prep_Time", "Difficulty", "image_path",
            ]
            tasting_columns = [
                "id", "date", "cocktail_name", "rating", "notes", "mood", "occasion", "location",
                "would_make_again", "change_next_time", "sweetness", "sourness", "bitterness",
                "booziness", "body", "aroma", "balance", "finish", "created_at",
            ]
            saved_view_columns = ["id", "name", "payload_json", "created_at"]
            tag_columns = ["id", "entity_type", "entity_rowid", "tag", "created_at"]

            alcohol_rows = read_sqlite_rows(
                sqlite_conn,
                "SELECT rowid AS id, * FROM alcohol_inventory",
                alcohol_columns,
            )
            cocktail_rows = read_sqlite_rows(
                sqlite_conn,
                "SELECT rowid AS id, * FROM cocktail_notes",
                cocktail_columns,
            )
            tasting_rows = read_sqlite_rows(
                sqlite_conn,
                "SELECT * FROM tasting_log",
                tasting_columns,
            )
            saved_view_rows = read_sqlite_rows(
                sqlite_conn,
                "SELECT * FROM saved_views",
                saved_view_columns,
            )
            tag_rows = read_sqlite_rows(
                sqlite_conn,
                "SELECT * FROM tags",
                tag_columns,
            )

            upsert_alcohol_sql = """
            INSERT INTO alcohol_inventory (
                id, "Brand", "Base_Liquor", "Type", "ABV", "Country",
                "Price_NZD_700ml", "Taste", "Substitute", "Availability", "image_path"
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                "Brand" = EXCLUDED."Brand",
                "Base_Liquor" = EXCLUDED."Base_Liquor",
                "Type" = EXCLUDED."Type",
                "ABV" = EXCLUDED."ABV",
                "Country" = EXCLUDED."Country",
                "Price_NZD_700ml" = EXCLUDED."Price_NZD_700ml",
                "Taste" = EXCLUDED."Taste",
                "Substitute" = EXCLUDED."Substitute",
                "Availability" = EXCLUDED."Availability",
                "image_path" = EXCLUDED."image_path"
            """

            upsert_cocktail_sql = """
            INSERT INTO cocktail_notes (
                id, "Cocktail_Name", "Ingredients", "Rating_Jason", "Rating_Jaime", "Rating_overall",
                "Base_spirit_1", "Type1", "Brand1", "Base_spirit_2", "Type2", "Brand2",
                "Citrus", "Garnish", "Notes", "DatetimeAdded", "Prep_Time", "Difficulty", "image_path"
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                "Cocktail_Name" = EXCLUDED."Cocktail_Name",
                "Ingredients" = EXCLUDED."Ingredients",
                "Rating_Jason" = EXCLUDED."Rating_Jason",
                "Rating_Jaime" = EXCLUDED."Rating_Jaime",
                "Rating_overall" = EXCLUDED."Rating_overall",
                "Base_spirit_1" = EXCLUDED."Base_spirit_1",
                "Type1" = EXCLUDED."Type1",
                "Brand1" = EXCLUDED."Brand1",
                "Base_spirit_2" = EXCLUDED."Base_spirit_2",
                "Type2" = EXCLUDED."Type2",
                "Brand2" = EXCLUDED."Brand2",
                "Citrus" = EXCLUDED."Citrus",
                "Garnish" = EXCLUDED."Garnish",
                "Notes" = EXCLUDED."Notes",
                "DatetimeAdded" = EXCLUDED."DatetimeAdded",
                "Prep_Time" = EXCLUDED."Prep_Time",
                "Difficulty" = EXCLUDED."Difficulty",
                "image_path" = EXCLUDED."image_path"
            """

            upsert_tasting_sql = """
            INSERT INTO tasting_log (
                id, date, cocktail_name, rating, notes, mood, occasion, location,
                would_make_again, change_next_time, sweetness, sourness, bitterness,
                booziness, body, aroma, balance, finish, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                date = EXCLUDED.date,
                cocktail_name = EXCLUDED.cocktail_name,
                rating = EXCLUDED.rating,
                notes = EXCLUDED.notes,
                mood = EXCLUDED.mood,
                occasion = EXCLUDED.occasion,
                location = EXCLUDED.location,
                would_make_again = EXCLUDED.would_make_again,
                change_next_time = EXCLUDED.change_next_time,
                sweetness = EXCLUDED.sweetness,
                sourness = EXCLUDED.sourness,
                bitterness = EXCLUDED.bitterness,
                booziness = EXCLUDED.booziness,
                body = EXCLUDED.body,
                aroma = EXCLUDED.aroma,
                balance = EXCLUDED.balance,
                finish = EXCLUDED.finish,
                created_at = EXCLUDED.created_at
            """

            upsert_saved_view_sql = """
            INSERT INTO saved_views (id, name, payload_json, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                payload_json = EXCLUDED.payload_json,
                created_at = EXCLUDED.created_at
            """

            upsert_tag_sql = """
            INSERT INTO tags (id, entity_type, entity_rowid, tag, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                entity_type = EXCLUDED.entity_type,
                entity_rowid = EXCLUDED.entity_rowid,
                tag = EXCLUDED.tag,
                created_at = EXCLUDED.created_at
            """

            migrated = {
                "alcohol_inventory": upsert_many(pg_conn, upsert_alcohol_sql, alcohol_rows),
                "cocktail_notes": upsert_many(pg_conn, upsert_cocktail_sql, cocktail_rows),
                "tasting_log": upsert_many(pg_conn, upsert_tasting_sql, tasting_rows),
                "saved_views": upsert_many(pg_conn, upsert_saved_view_sql, saved_view_rows),
                "tags": upsert_many(pg_conn, upsert_tag_sql, tag_rows),
            }
            pg_conn.commit()

            for table_name in migrated:
                source_count = count_table_sqlite(sqlite_conn, table_name)
                target_count = count_table_postgres(pg_conn, table_name)
                report["tables"][table_name] = {
                    "source_count": source_count,
                    "migrated_rows": migrated[table_name],
                    "target_count": target_count,
                    "count_match": source_count == target_count,
                }

    finally:
        sqlite_conn.close()

    report["all_counts_match"] = all(item["count_match"] for item in report["tables"].values())
    print(json.dumps(report, indent=2))
    return 0 if report["all_counts_match"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
