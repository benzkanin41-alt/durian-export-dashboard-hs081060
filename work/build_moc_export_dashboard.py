from __future__ import annotations

import csv
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE_URL = "https://tradereport.moc.go.th"
REPORT_URL = f"{BASE_URL}/th/stat/reporthscodeexport01"
RESULT_URL = f"{BASE_URL}/stat/reporthscodeexport01/result"
PRODUCT_NAME = "\u0e17\u0e38\u0e40\u0e23\u0e35\u0e22\u0e19"
HS_CODE = "081060"
HS_VERSION = "2022"
START_YEAR = 2021
START_MONTH = 1
MONTHS_TH = {
    1: "\u0e21.\u0e04.", 2: "\u0e01.\u0e1e.", 3: "\u0e21\u0e35.\u0e04.", 4: "\u0e40\u0e21.\u0e22.",
    5: "\u0e1e.\u0e04.", 6: "\u0e21\u0e34.\u0e22.", 7: "\u0e01.\u0e04.", 8: "\u0e2a.\u0e04.",
    9: "\u0e01.\u0e22.", 10: "\u0e15.\u0e04.", 11: "\u0e1e.\u0e22.", 12: "\u0e18.\u0e04.",
}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def write_pretty_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def parse_latest(html: str) -> tuple[int, int, str]:
    match = re.search(r'<report-hscode-export01[^>]*latestmonth="(\d+)"\s+latestyear="(\d+)"', html)
    if not match:
        raise RuntimeError("Could not find latest month and year on the MOC report page.")
    bundle_match = re.search(r'/js/app\.js\?id=([^"\']+)', html)
    return int(match.group(2)), int(match.group(1)), bundle_match.group(1) if bundle_match else ""


def periods_through(last_year: int, last_month: int) -> list[tuple[int, int]]:
    result = []
    year, month = START_YEAR, START_MONTH
    while (year, month) <= (last_year, last_month):
        result.append((year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return result


def report_payload(year: int, month: int, hs_item: dict) -> dict:
    return {
        "year": {"id": str(year), "text": str(year + 543)},
        "month": {"id": str(month), "text": MONTHS_TH[month]},
        "currency": {"id": "baht", "text": "\u0e1a\u0e32\u0e17"},
        "country": None,
        "hscodedigits": 2,
        "hscode": None,
        "sort": {"id": "value_desc", "text": "\u0e21\u0e39\u0e25\u0e04\u0e48\u0e32 (\u0e08\u0e32\u0e01\u0e21\u0e32\u0e01\u0e44\u0e1b\u0e19\u0e49\u0e2d\u0e22)"},
        "hscodes": [{"id": hs_item["Code"], "name": hs_item["Name"]}],
        "Previousyear": {"id": "0", "text": "0 \u0e1b\u0e35"},
        "hscodeversion": {"id": HS_VERSION, "text": HS_VERSION},
        "lang": "th",
    }


def build_country_reference(session: requests.Session, existing: dict) -> tuple[list[dict], list[dict], dict[str, dict]]:
    lookup = session.get(f"{BASE_URL}/lookup/country", timeout=45).json()
    groups = session.get(f"{BASE_URL}/lookup/countrygroup?lang=th", timeout=45).json()
    lookup_by_id = {str(item["id"]): item for item in lookup}
    existing_by_id = {str(item["countryId"]): item for item in existing["countries"]}
    groups = [group for group in groups if group["id"] in {"1A", "1B", "1C", "1D", "1E", "1F", "1G"}]

    continent_rows = [
        {
            "continentId": group["id"],
            "continentName": group["name"],
            "countryCount": len(group["countrys"]),
        }
        for group in groups
    ]
    mapping = {}
    for group in groups:
        for country in group["countrys"]:
            country_id = str(country["CountryID"])
            lookup_item = lookup_by_id.get(country_id, {})
            mapping[country_id] = {
                "countryId": country_id,
                "code": country["id"],
                "nameTh": country["name"],
                "nameEn": lookup_item.get("nameEn", existing_by_id.get(country_id, {}).get("nameEn", "")),
                "continentId": group["id"],
                "continentName": group["name"],
            }

    for country_id, country in existing_by_id.items():
        mapping.setdefault(country_id, country)
    countries = sorted(mapping.values(), key=lambda item: (item["continentId"], item["code"], item["countryId"]))
    return continent_rows, countries, mapping


def update_readme(path: Path, latest: dict, validation: dict) -> None:
    text = path.read_text(encoding="utf-8")
    latest_period = latest["period"]
    latest_th = f"{MONTHS_TH[latest['month']]} {latest['year'] + 543}"
    replacements = {
        r"`2021-01` \u0e16\u0e36\u0e07 `\d{4}-\d{2}`": f"`2021-01` \u0e16\u0e36\u0e07 `{latest_period}`",
        r"`[\u0e01-\u0e5b\.]+ \d{4}`": f"`{latest_th}`",
        r"`[\d,]+` \u0e1a\u0e32\u0e17": f"`{latest['value']:,.0f}` \u0e1a\u0e32\u0e17",
        r"`[\d,]+` \u0e2b\u0e19\u0e48\u0e27\u0e22\u0e15\u0e32\u0e21 source": f"`{latest['quantity']:,.0f}` \u0e2b\u0e19\u0e48\u0e27\u0e22\u0e15\u0e32\u0e21 source",
    }
    # Replace the snapshot section separately so YTD values are not confused with monthly values.
    snapshot = (
        "## Latest Snapshot\n\n"
        f"- \u0e21\u0e39\u0e25\u0e04\u0e48\u0e32\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14: `{latest['value']:,.0f}` \u0e1a\u0e32\u0e17\n"
        f"- \u0e1b\u0e23\u0e34\u0e21\u0e32\u0e13\u0e40\u0e14\u0e37\u0e2d\u0e19\u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14: `{latest['quantity']:,.0f}` \u0e2b\u0e19\u0e48\u0e27\u0e22\u0e15\u0e32\u0e21 source\n"
        f"- YTD \u0e21\u0e39\u0e25\u0e04\u0e48\u0e32: `{latest['ytdValue']:,.0f}` \u0e1a\u0e32\u0e17\n"
        f"- YTD \u0e1b\u0e23\u0e34\u0e21\u0e32\u0e13: `{latest['ytdQuantity']:,.0f}` \u0e2b\u0e19\u0e48\u0e27\u0e22\u0e15\u0e32\u0e21 source\n"
    )
    text = re.sub(r"## Latest Snapshot\n.*?(?=\n## )", snapshot, text, flags=re.S)
    text = re.sub(r"`2021-01` \u0e16\u0e36\u0e07 `\d{4}-\d{2}`", f"`2021-01` \u0e16\u0e36\u0e07 `{latest_period}`", text)
    text = re.sub(r"`[\u0e01-\u0e5b\.]+ \d{4}`", f"`{latest_th}`", text, count=1)
    text = re.sub(r"`\d+` \u0e40\u0e14\u0e37\u0e2d\u0e19", f"`{validation['monthsFetched']}` \u0e40\u0e14\u0e37\u0e2d\u0e19", text, count=2)
    text = re.sub(r"`[\d,]+` country-month rows", f"`{validation['countryRows']:,}` country-month rows", text)
    text = re.sub(r"Fetched UTC: `[^`]+`", f"Fetched UTC: `{datetime.now(timezone.utc).isoformat(timespec='seconds')}`", text)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    data_dir = repo / "data"
    raw_dir = repo / "work" / "moc_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    existing = json.loads((data_dir / "dataset.json").read_text(encoding="utf-8"))

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (compatible; MOC dashboard refresh)"
    report_page = session.get(REPORT_URL, timeout=45).text
    latest_year, latest_month, bundle_id = parse_latest(report_page)
    hs_item = session.post(f"{BASE_URL}/lookup/hscodelist{HS_CODE}/{HS_VERSION}", json={"lang": "th"}, timeout=45).json()
    continents, countries, country_map = build_country_reference(session, existing)
    expected_periods = periods_through(latest_year, latest_month)

    totals = []
    monthly = []
    reconciliation = []
    missing_continent_country_ids = set()
    for index, (year, month) in enumerate(expected_periods, start=1):
        for attempt in range(1, 7):
            response = session.post(RESULT_URL, json=report_payload(year, month, hs_item), timeout=60)
            if response.status_code != 403 or attempt == 6:
                response.raise_for_status()
                break
            delay = 15 * attempt
            print(f"{year}-{month:02d}: MOC rate limit, retrying in {delay}s")
            time.sleep(delay)
        result = response.json()
        period = f"{year}-{month:02d}"
        write_json(raw_dir / f"{period}.json", result)
        records = result.get("records", [])
        summary = next((row for row in records if row.get("RowType") == "S"), None)
        if not summary:
            raise RuntimeError(f"Missing world summary for {period}.")
        total = {
            "period": period,
            "year": year,
            "month": month,
            "quarter": (month - 1) // 3 + 1,
            "value": float(summary["ValueMonth"]),
            "quantity": float(summary["QuantityMonth"]),
            "ytdValue": float(summary["Value"]),
            "ytdQuantity": float(summary["Quantity"]),
        }
        totals.append(total)
        country_rows = []
        for row in records:
            if row.get("RowType") != "N":
                continue
            country_id = str(row.get("ID", ""))
            country = country_map.get(country_id)
            if not country:
                missing_continent_country_ids.add(country_id)
                continue
            country_rows.append({
                "period": period,
                "year": year,
                "month": month,
                "quarter": total["quarter"],
                "countryId": country_id,
                "countryCode": country["code"],
                "countryName": row.get("CountryName") or country["nameTh"],
                "continentId": country["continentId"],
                "continentName": country["continentName"],
                "value": float(row["ValueMonth"]),
                "quantity": float(row["QuantityMonth"]),
            })
        monthly.extend(country_rows)
        value_sum = sum(row["value"] for row in country_rows)
        quantity_sum = sum(row["quantity"] for row in country_rows)
        reconciliation.append({
            "period": period,
            "countryCount": len(country_rows),
            "worldValue": total["value"],
            "countryValueSum": value_sum,
            "valueDiff": value_sum - total["value"],
            "worldQuantity": total["quantity"],
            "countryQuantitySum": quantity_sum,
            "quantityDiff": quantity_sum - total["quantity"],
        })
        print(f"[{index}/{len(expected_periods)}] {period}: {len(country_rows)} country rows")
        time.sleep(1.0)

    if missing_continent_country_ids:
        raise RuntimeError(f"Unmapped source country IDs: {sorted(missing_continent_country_ids)}")
    max_value_diff = max(abs(row["valueDiff"]) for row in reconciliation)
    max_quantity_diff = max(abs(row["quantityDiff"]) for row in reconciliation)
    if max_value_diff != 0 or max_quantity_diff != 0:
        raise RuntimeError(f"Reconciliation failed: value={max_value_diff}, quantity={max_quantity_diff}")

    continent_totals = defaultdict(lambda: {"value": 0.0, "quantity": 0.0})
    for row in monthly:
        key = (row["period"], row["continentId"], row["continentName"])
        continent_totals[key]["value"] += row["value"]
        continent_totals[key]["quantity"] += row["quantity"]
    continent_rows = []
    for (period, continent_id, continent_name), measures in sorted(continent_totals.items()):
        year, month = (int(value) for value in period.split("-"))
        continent_rows.append({
            "period": period,
            "year": year,
            "month": month,
            "quarter": (month - 1) // 3 + 1,
            "continentId": continent_id,
            "continentName": continent_name,
            "value": measures["value"],
            "quantity": measures["quantity"],
        })

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    validation = {
        "monthsFetched": len(totals),
        "expectedMonths": len(expected_periods),
        "worldSummaryRows": len(totals),
        "countryRows": len(monthly),
        "maxAbsValueDiff": max_value_diff,
        "maxAbsQuantityDiff": max_quantity_diff,
        "missingContinentCountryIds": [],
    }
    metadata = {
        **existing["metadata"],
        "productName": PRODUCT_NAME,
        "hsCode": HS_CODE,
        "hsName": hs_item["Name"],
        "hsVersion": HS_VERSION,
        "reportUrl": REPORT_URL,
        "endpoint": RESULT_URL,
        "appBundleId": bundle_id,
        "fetchedAtUtc": fetched_at,
        "startPeriod": f"{START_YEAR}-{START_MONTH:02d}",
        "latestPeriod": totals[-1]["period"],
        "latestYear": latest_year,
        "latestMonth": latest_month,
    }
    dataset = {
        "metadata": metadata,
        "continents": continents,
        "countries": countries,
        "monthly": monthly,
        "totals": totals,
        "validation": validation,
    }
    write_pretty_json(data_dir / "dataset.json", dataset)
    (repo / "data.js").write_text("window.MOC_EXPORT_DATA = " + json.dumps(dataset, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    write_csv(data_dir / "monthly_total_hs081060.csv", totals, ["period", "year", "month", "quarter", "value", "quantity", "ytdValue", "ytdQuantity"])
    write_csv(data_dir / "monthly_country_hs081060.csv", monthly, ["period", "year", "month", "quarter", "countryId", "countryCode", "countryName", "continentId", "continentName", "value", "quantity"])
    write_csv(data_dir / "monthly_continent_hs081060.csv", continent_rows, ["period", "year", "month", "quarter", "continentId", "continentName", "value", "quantity"])
    write_csv(data_dir / "validation_reconciliation.csv", reconciliation, ["period", "countryCount", "worldValue", "countryValueSum", "valueDiff", "worldQuantity", "countryQuantitySum", "quantityDiff"])
    write_json(raw_dir / "run_metadata.json", {"fetchedAtUtc": fetched_at, "latestPeriod": totals[-1]["period"], "validation": validation})
    update_readme(repo / "README.md", totals[-1], validation)
    print(json.dumps({"latest": totals[-1], "validation": validation}, ensure_ascii=False))


if __name__ == "__main__":
    main()
