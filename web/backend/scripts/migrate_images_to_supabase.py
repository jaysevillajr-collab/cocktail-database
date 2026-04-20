from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

import psycopg
import requests


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
DEFAULT_IMAGES_ROOT = (REPO_ROOT / "images").resolve()


def normalize_db_image_key(raw_path: str) -> str:
    text = str(raw_path or "").strip().replace("\\", "/")
    if not text:
        return ""

    while text.startswith("./"):
        text = text[2:]

    lowered = text.lower()
    if lowered.startswith("images/"):
        text = text[7:]

    return text.strip("/")


def collect_files(images_root: Path) -> list[Path]:
    if not images_root.exists() or not images_root.is_dir():
        return []
    return [p for p in images_root.rglob("*") if p.is_file()]


def upload_file(supabase_url: str, service_role_key: str, bucket: str, file_path: Path, images_root: Path) -> dict[str, Any]:
    key = file_path.relative_to(images_root).as_posix().strip("/")
    url = f"{supabase_url}/storage/v1/object/{bucket}/{key}"

    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    with file_path.open("rb") as f:
        response = requests.post(url, headers=headers, data=f.read(), timeout=60)

    ok = 200 <= response.status_code < 300
    return {
        "key": key,
        "status_code": response.status_code,
        "ok": ok,
        "response": "" if ok else response.text,
    }


def list_bucket_keys(supabase_url: str, service_role_key: str, bucket: str) -> set[str]:
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }

    def walk(prefix: str = "") -> list[str]:
        url = f"{supabase_url}/storage/v1/object/list/{bucket}"
        payload = {"prefix": prefix, "limit": 1000, "offset": 0}
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        items = resp.json()
        keys: list[str] = []
        for item in items:
            name = str(item.get("name") or "").strip()
            item_id = str(item.get("id") or "").strip()
            if not name:
                continue
            next_prefix = f"{prefix}{name}" if not prefix else f"{prefix}/{name}"
            if item_id:
                keys.append(next_prefix)
            else:
                keys.extend(walk(next_prefix))
        return keys

    return set(walk(""))


def normalize_postgres_image_paths(
    pg_conn: psycopg.Connection,
    existing_keys: set[str],
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "alcohol_inventory": {"updated": 0, "missing_key": 0},
        "cocktail_notes": {"updated": 0, "missing_key": 0},
    }

    table_specs = [
        ("alcohol_inventory", "id"),
        ("cocktail_notes", "id"),
    ]

    with pg_conn.cursor() as cur:
        for table_name, id_col in table_specs:
            cur.execute(f"SELECT {id_col}, image_path FROM {table_name} WHERE COALESCE(TRIM(image_path), '') <> ''")
            rows = cur.fetchall()

            for row_id, image_path in rows:
                normalized = normalize_db_image_key(str(image_path))
                if not normalized:
                    continue

                if normalized not in existing_keys:
                    report[table_name]["missing_key"] += 1
                    continue

                if normalized == str(image_path):
                    continue

                cur.execute(
                    f"UPDATE {table_name} SET image_path = %s WHERE {id_col} = %s",
                    (normalized, row_id),
                )
                report[table_name]["updated"] += 1

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload local images to Supabase Storage and normalize image paths")
    parser.add_argument(
        "--images-root",
        default=os.getenv("COCKTAIL_IMAGES_PATH", str(DEFAULT_IMAGES_ROOT)),
        help="Local images root directory",
    )
    parser.add_argument(
        "--supabase-url",
        default=os.getenv("SUPABASE_URL", "").strip(),
        help="Supabase project URL",
    )
    parser.add_argument(
        "--service-role-key",
        default=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
        help="Supabase service role key",
    )
    parser.add_argument(
        "--bucket",
        default=os.getenv("SUPABASE_STORAGE_BUCKET", "images").strip(),
        help="Supabase storage bucket",
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("SUPABASE_DB_URL", "").strip(),
        help="Supabase Postgres URL",
    )
    args = parser.parse_args()

    images_root = Path(args.images_root).resolve()
    if not images_root.exists() or not images_root.is_dir():
        raise FileNotFoundError(f"Images root not found: {images_root}")

    if not args.supabase_url:
        raise ValueError("SUPABASE_URL is required")
    if not args.service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required")
    if not args.bucket:
        raise ValueError("SUPABASE_STORAGE_BUCKET is required")
    if not args.db_url:
        raise ValueError("SUPABASE_DB_URL is required")

    files = collect_files(images_root)
    upload_report: dict[str, Any] = {
        "images_root": str(images_root),
        "bucket": args.bucket,
        "found_files": len(files),
        "uploaded_ok": 0,
        "upload_failed": 0,
        "failures": [],
    }

    for file_path in files:
        result = upload_file(
            supabase_url=args.supabase_url,
            service_role_key=args.service_role_key,
            bucket=args.bucket,
            file_path=file_path,
            images_root=images_root,
        )
        if result["ok"]:
            upload_report["uploaded_ok"] += 1
        else:
            upload_report["upload_failed"] += 1
            upload_report["failures"].append(result)

    if upload_report["upload_failed"] > 0:
        print(json.dumps(upload_report, indent=2))
        return 2

    bucket_keys = list_bucket_keys(
        supabase_url=args.supabase_url,
        service_role_key=args.service_role_key,
        bucket=args.bucket,
    )

    with psycopg.connect(args.db_url, prepare_threshold=None) as pg_conn:
        pg_conn.autocommit = False
        path_report = normalize_postgres_image_paths(pg_conn, bucket_keys)
        pg_conn.commit()

    final_report = {
        "upload": upload_report,
        "bucket_key_count": len(bucket_keys),
        "path_normalization": path_report,
    }
    print(json.dumps(final_report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
