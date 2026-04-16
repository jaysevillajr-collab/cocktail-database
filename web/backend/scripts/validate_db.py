from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


REQUIRED_TABLES = ["alcohol_inventory", "cocktail_notes"]
OPTIONAL_TABLES = ["tasting_log"]


def default_db_path() -> Path:
    return Path(__file__).resolve().parents[3] / "cocktail_database.db"


def fetch_count(cur: sqlite3.Cursor, table_name: str) -> int:
    cur.execute("SELECT COUNT(*) FROM %s" % table_name)
    return int(cur.fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate cocktail SQLite DB structure and row counts")
    parser.add_argument("--db", default=str(default_db_path()), help="Path to SQLite database")
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    if not db_path.exists():
        raise FileNotFoundError("Database not found: %s" % db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        integrity_result = cur.fetchone()[0]

        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = set(row[0] for row in cur.fetchall())

        missing_required = [name for name in REQUIRED_TABLES if name not in existing_tables]
        optional_present = [name for name in OPTIONAL_TABLES if name in existing_tables]

        counts = {}
        for table_name in REQUIRED_TABLES + optional_present:
            counts[table_name] = fetch_count(cur, table_name)

        report = {
            "db_path": str(db_path),
            "integrity_check": integrity_result,
            "required_tables": REQUIRED_TABLES,
            "missing_required_tables": missing_required,
            "optional_tables_present": optional_present,
            "counts": counts,
            "is_valid": integrity_result == "ok" and len(missing_required) == 0,
        }

        print(json.dumps(report, indent=2))
        return 0 if report["is_valid"] else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
