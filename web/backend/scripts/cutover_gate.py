from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests


def run_script(script_path: Path, args: List[str]) -> Dict[str, Any]:
    cmd = [sys.executable, str(script_path)] + args
    proc = subprocess.run(cmd, capture_output=True, text=True)

    payload = {
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "ok": proc.returncode == 0,
    }

    try:
        payload["json"] = json.loads(proc.stdout) if proc.stdout.strip() else None
    except Exception:
        payload["json"] = None

    return payload


def check_endpoints(api_base: str) -> Dict[str, Any]:
    endpoints = [
        "/health",
        "/meta/counts",
        "/alcohol?limit=1&offset=0",
        "/cocktails?limit=1&offset=0",
        "/tasting-logs",
        "/saved-views",
        "/tags",
        "/analytics/cost-insights",
    ]

    results = []
    for endpoint in endpoints:
        url = f"{api_base.rstrip('/')}{endpoint}"
        try:
            response = requests.get(url, timeout=20)
            results.append({"endpoint": endpoint, "status_code": response.status_code, "ok": response.ok})
        except Exception as exc:
            results.append({"endpoint": endpoint, "status_code": None, "ok": False, "error": str(exc)})

    return {
        "results": results,
        "ok": all(item.get("ok") for item in results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run parallel-run cutover gate checks")
    parser.add_argument("--api-base", default="http://127.0.0.1:8001", help="Backend API base URL")
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parents[3] / "cocktail_database.db"),
        help="SQLite DB path for integrity validation",
    )
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    validate_script = scripts_dir / "validate_db.py"
    parity_script = scripts_dir / "smoke_crud_parity.py"

    validate_result = run_script(validate_script, ["--db", args.db])
    endpoint_result = check_endpoints(args.api_base)
    parity_result = run_script(parity_script, ["--api-base", args.api_base])

    gate = {
        "api_base": args.api_base,
        "db": str(Path(args.db).resolve()),
        "checks": {
            "db_validation": validate_result,
            "endpoint_health": endpoint_result,
            "crud_parity_smoke": parity_result,
        },
        "manual_checklist_path": str((Path(__file__).resolve().parents[1] / "CUTOVER_CHECKLIST.md").resolve()),
    }

    gate["ready_for_cutover"] = bool(
        validate_result.get("ok")
        and endpoint_result.get("ok")
        and parity_result.get("ok")
    )

    print(json.dumps(gate, indent=2))
    return 0 if gate["ready_for_cutover"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
