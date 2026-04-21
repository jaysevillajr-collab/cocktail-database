from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

import psycopg
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


load_env_file()


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_PATH = (REPO_ROOT / "cocktail_database.db").resolve()


def format_score(value: float) -> str:
    clamped = max(0.0, min(5.0, value))
    if clamped.is_integer():
        return str(int(clamped))
    return str(round(clamped, 1))


def parse_numeric(raw: Any) -> float | None:
    text = str(raw or "").strip()
    if not text:
        return None
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def normalize_score(raw: Any) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return ""
    numeric = parse_numeric(text)
    if numeric is None:
        return None
    return format_score(numeric)


def normalize_abv(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    return text if "%" in text else f"{text}%"


def normalize_price(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    return text if text.startswith("$") else f"${text}"


def normalize_cocktail_fields(row: Dict[str, Any]) -> Tuple[Dict[str, str], List[str]]:
    updates: Dict[str, str] = {}
    issues: List[str] = []
    for field in ("Rating_Jason", "Rating_Jaime", "Rating_overall", "Difficulty"):
        original = str(row.get(field) or "")
        normalized = normalize_score(original)
        if normalized is None:
            if original.strip():
                issues.append(f"{field}:non-numeric")
            continue
        if normalized != original:
            updates[field] = normalized
    return updates, issues


def normalize_tasting_fields(row: Dict[str, Any]) -> Tuple[Dict[str, str], List[str]]:
    updates: Dict[str, str] = {}
    issues: List[str] = []
    original = str(row.get("rating") or "")
    normalized = normalize_score(original)
    if normalized is None:
        if original.strip():
            issues.append("rating:non-numeric")
    elif normalized != original:
        updates["rating"] = normalized
    return updates, issues


def normalize_alcohol_fields(row: Dict[str, Any]) -> Tuple[Dict[str, str], List[str]]:
    updates: Dict[str, str] = {}
    issues: List[str] = []

    abv_original = str(row.get("ABV") or "")
    abv_next = normalize_abv(abv_original)
    if abv_next != abv_original:
        updates["ABV"] = abv_next

    price_original = str(row.get("Price_NZD_700ml") or "")
    price_next = normalize_price(price_original)
    if price_next != price_original:
        updates["Price_NZD_700ml"] = price_next

    return updates, issues


def process_sqlite(sqlite_path: Path, apply: bool) -> Dict[str, Any]:
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row

    report: Dict[str, Any] = {
        "path": str(sqlite_path),
        "tables": {
            "alcohol_inventory": {"rows_changed": 0, "issues": 0},
            "cocktail_notes": {"rows_changed": 0, "issues": 0},
            "tasting_log": {"rows_changed": 0, "issues": 0},
        },
    }

    try:
        cur = conn.cursor()

        cur.execute("SELECT rowid, * FROM alcohol_inventory")
        for row in [dict(item) for item in cur.fetchall()]:
            updates, issues = normalize_alcohol_fields(row)
            report["tables"]["alcohol_inventory"]["issues"] += len(issues)
            if not updates:
                continue
            report["tables"]["alcohol_inventory"]["rows_changed"] += 1
            if apply:
                cur.execute(
                    "UPDATE alcohol_inventory SET ABV = ?, Price_NZD_700ml = ? WHERE rowid = ?",
                    (updates.get("ABV", row.get("ABV", "")), updates.get("Price_NZD_700ml", row.get("Price_NZD_700ml", "")), row["rowid"]),
                )

        cur.execute("SELECT rowid, * FROM cocktail_notes")
        for row in [dict(item) for item in cur.fetchall()]:
            updates, issues = normalize_cocktail_fields(row)
            report["tables"]["cocktail_notes"]["issues"] += len(issues)
            if not updates:
                continue
            report["tables"]["cocktail_notes"]["rows_changed"] += 1
            if apply:
                cur.execute(
                    """
                    UPDATE cocktail_notes
                    SET Rating_Jason = ?, Rating_Jaime = ?, Rating_overall = ?, Difficulty = ?
                    WHERE rowid = ?
                    """,
                    (
                        updates.get("Rating_Jason", row.get("Rating_Jason", "")),
                        updates.get("Rating_Jaime", row.get("Rating_Jaime", "")),
                        updates.get("Rating_overall", row.get("Rating_overall", "")),
                        updates.get("Difficulty", row.get("Difficulty", "")),
                        row["rowid"],
                    ),
                )

        cur.execute("SELECT id, rating FROM tasting_log")
        for row in [dict(item) for item in cur.fetchall()]:
            updates, issues = normalize_tasting_fields(row)
            report["tables"]["tasting_log"]["issues"] += len(issues)
            if not updates:
                continue
            report["tables"]["tasting_log"]["rows_changed"] += 1
            if apply:
                cur.execute(
                    "UPDATE tasting_log SET rating = ? WHERE id = ?",
                    (updates["rating"], row["id"]),
                )

        if apply:
            conn.commit()
    finally:
        conn.close()

    return report


def process_supabase(db_url: str, apply: bool) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "tables": {
            "alcohol_inventory": {"rows_changed": 0, "issues": 0},
            "cocktail_notes": {"rows_changed": 0, "issues": 0},
            "tasting_log": {"rows_changed": 0, "issues": 0},
        },
    }

    with psycopg.connect(db_url, prepare_threshold=None, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id, "ABV", "Price_NZD_700ml" FROM alcohol_inventory')
            alcohol_rows = [dict(item) for item in cur.fetchall()]
            for row in alcohol_rows:
                updates, issues = normalize_alcohol_fields(row)
                report["tables"]["alcohol_inventory"]["issues"] += len(issues)
                if not updates:
                    continue
                report["tables"]["alcohol_inventory"]["rows_changed"] += 1
                if apply:
                    cur.execute(
                        'UPDATE alcohol_inventory SET "ABV" = %s, "Price_NZD_700ml" = %s WHERE id = %s',
                        (
                            updates.get("ABV", row.get("ABV", "")),
                            updates.get("Price_NZD_700ml", row.get("Price_NZD_700ml", "")),
                            row["id"],
                        ),
                    )

            cur.execute('SELECT id, "Rating_Jason", "Rating_Jaime", "Rating_overall", "Difficulty" FROM cocktail_notes')
            cocktail_rows = [dict(item) for item in cur.fetchall()]
            for row in cocktail_rows:
                updates, issues = normalize_cocktail_fields(row)
                report["tables"]["cocktail_notes"]["issues"] += len(issues)
                if not updates:
                    continue
                report["tables"]["cocktail_notes"]["rows_changed"] += 1
                if apply:
                    cur.execute(
                        'UPDATE cocktail_notes SET "Rating_Jason" = %s, "Rating_Jaime" = %s, "Rating_overall" = %s, "Difficulty" = %s WHERE id = %s',
                        (
                            updates.get("Rating_Jason", row.get("Rating_Jason", "")),
                            updates.get("Rating_Jaime", row.get("Rating_Jaime", "")),
                            updates.get("Rating_overall", row.get("Rating_overall", "")),
                            updates.get("Difficulty", row.get("Difficulty", "")),
                            row["id"],
                        ),
                    )

            cur.execute('SELECT id, rating FROM tasting_log')
            tasting_rows = [dict(item) for item in cur.fetchall()]
            for row in tasting_rows:
                updates, issues = normalize_tasting_fields(row)
                report["tables"]["tasting_log"]["issues"] += len(issues)
                if not updates:
                    continue
                report["tables"]["tasting_log"]["rows_changed"] += 1
                if apply:
                    cur.execute(
                        'UPDATE tasting_log SET rating = %s WHERE id = %s',
                        (updates["rating"], row["id"]),
                    )

        if apply:
            conn.commit()

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize rating/difficulty to 0-5 and format ABV/price across SQLite + Supabase")
    parser.add_argument(
        "--sqlite-path",
        default=os.getenv("COCKTAIL_DB_PATH", str(DEFAULT_SQLITE_PATH)),
        help="Path to SQLite DB (defaults to COCKTAIL_DB_PATH or repo cocktail_database.db)",
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("SUPABASE_DB_URL", "").strip(),
        help="Supabase Postgres URL (defaults to SUPABASE_DB_URL)",
    )
    parser.add_argument("--skip-sqlite", action="store_true", help="Skip SQLite normalization")
    parser.add_argument("--skip-supabase", action="store_true", help="Skip Supabase normalization")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite_path).resolve()
    if not args.skip_sqlite and not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    report: Dict[str, Any] = {"mode": "apply" if args.apply else "dry-run"}

    if not args.skip_sqlite:
        report["sqlite"] = process_sqlite(sqlite_path, apply=args.apply)

    if not args.skip_supabase:
        db_url = str(args.db_url or "").strip()
        if not db_url:
            raise ValueError("SUPABASE_DB_URL is required unless --skip-supabase is used")
        report["supabase"] = process_supabase(db_url, apply=args.apply)

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
