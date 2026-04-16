from __future__ import annotations

import argparse
import json
import time
from typing import Dict, Optional

import requests


def request_json(method: str, url: str, **kwargs):
    response = requests.request(method, url, timeout=20, **kwargs)
    response.raise_for_status()
    return response.json()


def get_counts(api_base: str) -> Dict[str, int]:
    payload = request_json("GET", f"{api_base}/meta/counts")
    return {
        "alcohol_inventory": int(payload.get("alcohol_inventory", 0)),
        "cocktail_notes": int(payload.get("cocktail_notes", 0)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test CRUD parity endpoints and validate no count drift")
    parser.add_argument("--api-base", default="http://127.0.0.1:8001", help="Backend API base URL")
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    run_id = str(int(time.time()))

    created_alcohol_rowid: Optional[int] = None
    created_cocktail_rowid: Optional[int] = None

    report = {
        "api_base": api_base,
        "run_id": run_id,
        "steps": [],
        "status": "running",
    }

    baseline_counts = get_counts(api_base)
    report["baseline_counts"] = baseline_counts

    try:
        alcohol_payload = {
            "Brand": f"CascadeSmokeAlcohol-{run_id}",
            "Base_Liquor": "SmokeTest",
            "Type": "Temp",
            "ABV": "0",
            "Country": "NZ",
            "Price_NZD_700ml": "$0",
            "Taste": "smoke test",
            "Substitute": "",
            "Availability": "Yes",
            "image_path": "",
        }

        created_alcohol = request_json(
            "POST",
            f"{api_base}/alcohol",
            json=alcohol_payload,
            headers={"Content-Type": "application/json"},
        )
        created_alcohol_rowid = int(created_alcohol["item"]["_rowid"])
        report["steps"].append({"name": "create_alcohol", "rowid": created_alcohol_rowid, "ok": True})

        alcohol_update_payload = dict(alcohol_payload)
        alcohol_update_payload["Type"] = "Temp Updated"
        request_json(
            "PUT",
            f"{api_base}/alcohol/id/{created_alcohol_rowid}",
            json=alcohol_update_payload,
            headers={"Content-Type": "application/json"},
        )
        report["steps"].append({"name": "update_alcohol", "rowid": created_alcohol_rowid, "ok": True})

        cocktail_payload = {
            "Cocktail_Name": f"CascadeSmokeCocktail-{run_id}",
            "Ingredients": "1 oz test spirit, 1 oz test syrup",
            "Rating_Jason": "0",
            "Rating_Jaime": "0",
            "Rating_overall": "0",
            "Base_spirit_1": "SmokeTest",
            "Type1": "Temp",
            "Brand1": "Temp",
            "Base_spirit_2": "",
            "Type2": "",
            "Brand2": "",
            "Citrus": "",
            "Garnish": "",
            "Notes": "smoke test",
            "DatetimeAdded": "",
            "Prep_Time": "",
            "Difficulty": "1",
            "image_path": "",
        }

        created_cocktail = request_json(
            "POST",
            f"{api_base}/cocktails",
            json=cocktail_payload,
            headers={"Content-Type": "application/json"},
        )
        created_cocktail_rowid = int(created_cocktail["item"]["_rowid"])
        report["steps"].append({"name": "create_cocktail", "rowid": created_cocktail_rowid, "ok": True})

        cocktail_update_payload = dict(cocktail_payload)
        cocktail_update_payload["Difficulty"] = "2"
        request_json(
            "PUT",
            f"{api_base}/cocktails/id/{created_cocktail_rowid}",
            json=cocktail_update_payload,
            headers={"Content-Type": "application/json"},
        )
        report["steps"].append({"name": "update_cocktail", "rowid": created_cocktail_rowid, "ok": True})

    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
    finally:
        if created_alcohol_rowid is not None:
            try:
                request_json("DELETE", f"{api_base}/alcohol/id/{created_alcohol_rowid}")
                report["steps"].append({"name": "delete_alcohol", "rowid": created_alcohol_rowid, "ok": True})
            except Exception as exc:
                report["steps"].append({"name": "delete_alcohol", "rowid": created_alcohol_rowid, "ok": False, "error": str(exc)})

        if created_cocktail_rowid is not None:
            try:
                request_json("DELETE", f"{api_base}/cocktails/id/{created_cocktail_rowid}")
                report["steps"].append({"name": "delete_cocktail", "rowid": created_cocktail_rowid, "ok": True})
            except Exception as exc:
                report["steps"].append({"name": "delete_cocktail", "rowid": created_cocktail_rowid, "ok": False, "error": str(exc)})

    final_counts = get_counts(api_base)
    report["final_counts"] = final_counts
    report["count_drift"] = {
        "alcohol_inventory": final_counts["alcohol_inventory"] - baseline_counts["alcohol_inventory"],
        "cocktail_notes": final_counts["cocktail_notes"] - baseline_counts["cocktail_notes"],
    }

    all_steps_ok = all(step.get("ok") for step in report["steps"])
    no_drift = report["count_drift"]["alcohol_inventory"] == 0 and report["count_drift"]["cocktail_notes"] == 0
    if report.get("status") != "failed":
        report["status"] = "passed" if (all_steps_ok and no_drift) else "failed"

    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
