from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


def default_db_path() -> Path:
    return Path(__file__).resolve().parents[3] / "cocktail_database.db"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create timestamped backup for cocktail SQLite DB")
    parser.add_argument("--db", default=str(default_db_path()), help="Path to source SQLite database")
    parser.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parents[1] / "backups"),
        help="Directory where backup files are written",
    )
    args = parser.parse_args()

    src = Path(args.db).resolve()
    out_dir = Path(args.out_dir).resolve()

    if not src.exists():
        raise FileNotFoundError("Database not found: %s" % src)

    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = out_dir / ("cocktail_database-%s.db" % stamp)

    shutil.copy2(str(src), str(backup_path))

    report = {
        "source": str(src),
        "backup": str(backup_path),
        "source_size_bytes": src.stat().st_size,
        "backup_size_bytes": backup_path.stat().st_size,
        "sha256": sha256_file(backup_path),
        "timestamp": stamp,
    }

    report_path = out_dir / ("cocktail_database-%s.json" % stamp)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
