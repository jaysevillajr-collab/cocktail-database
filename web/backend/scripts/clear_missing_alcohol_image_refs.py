from __future__ import annotations

import os
from pathlib import Path

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


def normalize_key(path_value: str) -> str:
    value = str(path_value or "").strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    if value.lower().startswith("images/"):
        value = value[7:]
    return value.strip("/")


def list_bucket_keys(supabase_url: str, service_role_key: str, bucket: str) -> set[str]:
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }

    def walk(prefix: str = "") -> list[str]:
        response = requests.post(
            f"{supabase_url}/storage/v1/object/list/{bucket}",
            headers=headers,
            json={"prefix": prefix, "limit": 1000, "offset": 0},
            timeout=60,
        )
        response.raise_for_status()
        items = response.json()

        keys: list[str] = []
        for item in items:
            name = str(item.get("name") or "").strip()
            item_id = str(item.get("id") or "").strip()
            if not name:
                continue
            next_prefix = f"{prefix}/{name}" if prefix else name
            if item_id:
                keys.append(next_prefix)
            else:
                keys.extend(walk(next_prefix))
        return keys

    return set(walk(""))


def main() -> int:
    load_env_file()

    supabase_url = str(os.getenv("SUPABASE_URL", "")).strip()
    service_role_key = str(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
    db_url = str(os.getenv("SUPABASE_DB_URL", "")).strip()
    bucket = str(os.getenv("SUPABASE_STORAGE_BUCKET", "images")).strip() or "images"

    if not supabase_url:
        raise ValueError("SUPABASE_URL is required")
    if not service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required")
    if not db_url:
        raise ValueError("SUPABASE_DB_URL is required")

    bucket_keys = list_bucket_keys(supabase_url, service_role_key, bucket)

    scanned = 0
    cleared = 0

    with psycopg.connect(db_url, prepare_threshold=None) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, image_path
                FROM alcohol_inventory
                WHERE COALESCE(TRIM(image_path), '') <> ''
                """
            )
            rows = cur.fetchall()
            scanned = len(rows)

            for row_id, image_path in rows:
                normalized = normalize_key(str(image_path))
                if not normalized:
                    continue
                if normalized not in bucket_keys:
                    cur.execute(
                        "UPDATE alcohol_inventory SET image_path = %s WHERE id = %s",
                        ("", row_id),
                    )
                    cleared += 1

        conn.commit()

    print(
        {
            "bucket": bucket,
            "bucket_keys": len(bucket_keys),
            "alcohol_rows_scanned": scanned,
            "alcohol_image_refs_cleared": cleared,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
