#!/usr/bin/env python3
"""Collect SEC EDGAR 10-K reports for Fortune 2025 top-ranked firms.

This script uses official SEC data endpoints:
- https://www.sec.gov/files/company_tickers.json
- https://data.sec.gov/submissions/CIK##########.json
- https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primaryDocument}

The matching stage is intentionally conservative. It creates a manifest and audit
log and does not claim that every Fortune company has SEC 10-K coverage.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.request
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from x_scrapper.paths import AUDIT_ROOT, CONFIG_ROOT, DATA_ROOT, REPO_ROOT
from typing import Any

DEFAULT_INPUT = REPO_ROOT / "fortune2025_itemListElement_rows.csv"
DEFAULT_MANIFEST = CONFIG_ROOT / "fortune2025_top100_10k_report_index.csv"
DEFAULT_AUDIT = AUDIT_ROOT / "fortune2025_top100_10k_report_audit.csv"
DEFAULT_REPORT_DIR = DATA_ROOT / "sec_10k" / "reports"
DEFAULT_YEARS = (2025, 2024, 2023)
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_no_dash}/{primary_doc}"

MANIFEST_FIELDS = [
    "fortune_year",
    "fortune_rank",
    "firm_name",
    "fortune_company_url",
    "target_report_year",
    "sec_cik",
    "sec_company_name",
    "sec_ticker",
    "sec_match_score",
    "sec_match_status",
    "form",
    "filing_date",
    "report_date",
    "accession_number",
    "primary_document",
    "sec_filing_url",
    "local_report_path",
    "download_status",
    "status",
    "notes",
    "collected_at",
]

AUDIT_FIELDS = [
    "fortune_rank",
    "firm_name",
    "target_report_year",
    "status",
    "error_type",
    "error_message",
    "sec_cik",
    "sec_company_name",
    "sec_match_score",
    "sec_filing_url",
    "local_report_path",
    "attempted_at",
]

LEGAL_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "company", "co", "group", "holdings",
    "holding", "plc", "llc", "ltd", "limited", "sa", "ag", "nv", "lp", "the",
}

ALIASES = {
    "amazon": "amazon com",
    "walmart": "walmart",
    "unitedhealth group": "unitedhealth group",
    "apple": "apple",
    "alphabet": "alphabet",
    "cvs health": "cvs health",
    "berkshire hathaway": "berkshire hathaway",
    "mckesson": "mckesson",
    "exxon mobil": "exxon mobil",
    "cencora": "cencora",
    "jpmorgan chase": "jpmorgan chase",
    "costco wholesale": "costco wholesale",
    "cigna group": "cigna group",
    "nvidia": "nvidia",
    "meta platforms": "meta platforms",
    "elevance health": "elevance health",
    "bank of america": "bank of america",
    "ford motor": "ford motor",
    "general motors": "general motors",
    "fannie mae": "fannie mae",
    "home depot": "home depot",
    "marathon petroleum": "marathon petroleum",
    "walgreens boots alliance": "walgreens boots alliance",
    "lowe's": "lowes companies",
    "johnson & johnson": "johnson johnson",
    "fedex": "fedex",
    "humana": "humana",
    "wells fargo": "wells fargo",
    "state farm insurance": "state farm",
    "pfizer": "pfizer",
    "pepsico": "pepsico",
    "comcast": "comcast",
    "disney": "walt disney",
    "lockheed martin": "lockheed martin",
    "goldman sachs group": "goldman sachs group",
    "morgan stanley": "morgan stanley",
    "raytheon technologies": "rtx",
    "caterpillar": "caterpillar",
    "intel": "intel",
    "nike": "nike",
    "oracle": "oracle",
    "tesla": "tesla",
    "cisco systems": "cisco systems",
    "coca-cola": "coca cola",
    "american express": "american express",
    "netflix": "netflix",
    "eli lilly": "eli lilly",
    "merck": "merck",
    "qualcomm": "qualcomm",
    "starbucks": "starbucks",
    "blackrock": "blackrock",
    "paypal holdings": "paypal holdings",
    "honeywell international": "honeywell international",
    "salesforce": "salesforce",
}


@dataclass
class FortuneFirm:
    fortune_year: str
    fortune_rank: int
    firm_name: str
    fortune_company_url: str


@dataclass
class SecCompany:
    cik: str
    title: str
    ticker: str
    norm_title: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_name(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    tokens = [token for token in value.split() if token not in LEGAL_SUFFIXES]
    return " ".join(tokens).strip()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "firm"


def read_fortune_firms(path: Path, limit: int) -> list[FortuneFirm]:
    firms: list[FortuneFirm] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rank = int(row["fortune 2025 rank"])
            if rank > limit:
                continue
            firms.append(FortuneFirm("2025", rank, row["name"].strip(), row.get("id", "").strip()))
    return sorted(firms, key=lambda item: item.fortune_rank)


def request_bytes(url: str, user_agent: str, delay: float, retries: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": user_agent,
                    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Encoding": "identity",
                    "Host": urllib.parse.urlparse(url).netloc,
                },
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read()
            time.sleep(delay)
            return data
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = exc
            time.sleep(delay * attempt)
    raise RuntimeError(f"Request failed after {retries} attempts: {url}: {last_error}")


def load_sec_companies(cache_dir: Path, user_agent: str, delay: float, refresh: bool) -> list[SecCompany]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "company_tickers.json"
    if refresh or not cache_path.exists():
        cache_path.write_bytes(request_bytes(SEC_TICKERS_URL, user_agent, delay))
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    companies: list[SecCompany] = []
    for item in payload.values():
        cik = str(item["cik_str"]).zfill(10)
        title = str(item.get("title", "")).strip()
        ticker = str(item.get("ticker", "")).strip()
        companies.append(SecCompany(cik, title, ticker, normalize_name(title)))
    return companies


def company_score(firm_name: str, company: SecCompany) -> float:
    firm_key = normalize_name(ALIASES.get(firm_name.lower(), firm_name))
    title = company.norm_title
    if not firm_key or not title:
        return 0.0
    if firm_key == title:
        return 100.0
    if firm_key in title or title in firm_key:
        return 92.0
    firm_tokens = set(firm_key.split())
    title_tokens = set(title.split())
    overlap = len(firm_tokens & title_tokens) / max(1, len(firm_tokens | title_tokens))
    ratio = SequenceMatcher(None, firm_key, title).ratio()
    return round(max(ratio * 100, overlap * 100), 2)


def best_sec_match(firm: FortuneFirm, companies: list[SecCompany], threshold: float) -> tuple[SecCompany | None, float, str]:
    scored = sorted(((company_score(firm.firm_name, company), company) for company in companies), reverse=True, key=lambda item: item[0])
    if not scored or scored[0][0] < threshold:
        return None, scored[0][0] if scored else 0.0, "no_confident_cik_match"
    top_score, top_company = scored[0]
    if len(scored) > 1 and top_score - scored[1][0] < 3 and top_score < 95:
        return top_company, top_score, "ambiguous_cik_match"
    return top_company, top_score, "matched"


def load_submissions(cik10: str, cache_dir: Path, user_agent: str, delay: float, refresh: bool) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"CIK{cik10}.json"
    if refresh or not cache_path.exists():
        cache_path.write_bytes(request_bytes(SEC_SUBMISSIONS_URL.format(cik10=cik10), user_agent, delay))
    return json.loads(cache_path.read_text(encoding="utf-8"))


def find_10k(submissions: dict[str, Any], target_year: int) -> dict[str, str] | None:
    recent = submissions.get("filings", {}).get("recent", {})
    rows = []
    for index, form in enumerate(recent.get("form", [])):
        if form not in {"10-K", "10-K/A"}:
            continue
        report_date = str(recent.get("reportDate", [""])[index] or "")
        if not report_date.startswith(str(target_year)):
            continue
        rows.append({
            "form": form,
            "filing_date": str(recent.get("filingDate", [""])[index] or ""),
            "report_date": report_date,
            "accession_number": str(recent.get("accessionNumber", [""])[index] or ""),
            "primary_document": str(recent.get("primaryDocument", [""])[index] or ""),
        })
    rows.sort(key=lambda row: (row["form"] != "10-K", row["filing_date"]), reverse=False)
    exact = [row for row in rows if row["form"] == "10-K"]
    return (exact or rows)[0] if rows else None


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)



def build_source_failure_outputs(args: argparse.Namespace, error: Exception) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    firms = read_fortune_firms(args.input, args.rank_limit)
    collected_at = now_iso()
    manifest: list[dict[str, str]] = []
    audit: list[dict[str, str]] = []
    message = f"SEC source fetch failed before CIK matching: {type(error).__name__}: {str(error)[:400]}"
    for firm in firms:
        for year in args.years:
            row = {
                "fortune_year": firm.fortune_year,
                "fortune_rank": str(firm.fortune_rank),
                "firm_name": firm.firm_name,
                "fortune_company_url": firm.fortune_company_url,
                "target_report_year": str(year),
                "sec_cik": "",
                "sec_company_name": "",
                "sec_ticker": "",
                "sec_match_score": "0.00",
                "sec_match_status": "sec_source_fetch_failed",
                "form": "",
                "filing_date": "",
                "report_date": "",
                "accession_number": "",
                "primary_document": "",
                "sec_filing_url": "",
                "local_report_path": "",
                "download_status": "not_attempted",
                "status": "sec_source_fetch_failed",
                "notes": message,
                "collected_at": collected_at,
            }
            manifest.append(row)
            audit.append({
                "fortune_rank": row["fortune_rank"],
                "firm_name": row["firm_name"],
                "target_report_year": row["target_report_year"],
                "status": row["status"],
                "error_type": type(error).__name__,
                "error_message": message,
                "sec_cik": "",
                "sec_company_name": "",
                "sec_match_score": "0.00",
                "sec_filing_url": "",
                "local_report_path": "",
                "attempted_at": collected_at,
            })
    return manifest, audit

def collect(args: argparse.Namespace) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    user_agent = args.user_agent or "Vulter3653 x_scrapper research contact@example.com"
    firms = read_fortune_firms(args.input, args.rank_limit)
    try:
        companies = load_sec_companies(args.cache_dir, user_agent, args.delay_seconds, args.refresh_cache)
    except Exception as exc:
        print(f"SEC source fetch failed: {type(exc).__name__}: {exc}", flush=True)
        return build_source_failure_outputs(args, exc)
    manifest: list[dict[str, str]] = []
    audit: list[dict[str, str]] = []
    collected_at = now_iso()

    for firm in firms:
        company, score, match_status = best_sec_match(firm, companies, args.match_threshold)
        submissions: dict[str, Any] | None = None
        if company and match_status in {"matched", "ambiguous_cik_match"}:
            try:
                submissions = load_submissions(company.cik, args.cache_dir / "submissions", user_agent, args.delay_seconds, args.refresh_cache)
            except Exception as exc:
                submissions = None
                match_status = "submissions_fetch_failed"
                fetch_error = exc
            else:
                fetch_error = None
        else:
            fetch_error = None

        for year in args.years:
            base = {
                "fortune_year": firm.fortune_year,
                "fortune_rank": str(firm.fortune_rank),
                "firm_name": firm.firm_name,
                "fortune_company_url": firm.fortune_company_url,
                "target_report_year": str(year),
                "sec_cik": company.cik if company else "",
                "sec_company_name": company.title if company else "",
                "sec_ticker": company.ticker if company else "",
                "sec_match_score": f"{score:.2f}",
                "sec_match_status": match_status,
                "form": "",
                "filing_date": "",
                "report_date": "",
                "accession_number": "",
                "primary_document": "",
                "sec_filing_url": "",
                "local_report_path": "",
                "download_status": "not_attempted",
                "status": "",
                "notes": "",
                "collected_at": collected_at,
            }
            if not company:
                base["status"] = "no_cik_match"
                base["notes"] = "No confident SEC CIK match from SEC company_tickers.json. Private company or name mismatch possible."
            elif fetch_error:
                base["status"] = "submissions_fetch_failed"
                base["notes"] = str(fetch_error)[:500]
            else:
                filing = find_10k(submissions or {}, year)
                if not filing:
                    base["status"] = "no_10k_for_year"
                    base["notes"] = "No 10-K/10-K/A found in SEC recent submissions for the target report year."
                else:
                    accession_no_dash = filing["accession_number"].replace("-", "")
                    url = SEC_ARCHIVES_URL.format(cik_int=str(int(company.cik)), accession_no_dash=accession_no_dash, primary_doc=filing["primary_document"])
                    base.update(filing)
                    base["sec_filing_url"] = url
                    base["status"] = "found"
                    base["notes"] = "SEC 10-K candidate found by reportDate year."
                    if args.download:
                        local_path = args.report_dir / f"rank_{firm.fortune_rank:03d}_{slug(firm.firm_name)}" / str(year) / filing["primary_document"]
                        try:
                            local_path.parent.mkdir(parents=True, exist_ok=True)
                            if args.refresh_downloads or not local_path.exists():
                                local_path.write_bytes(request_bytes(url, user_agent, args.delay_seconds))
                            base["local_report_path"] = str(local_path)
                            base["download_status"] = "downloaded"
                        except Exception as exc:
                            base["download_status"] = "download_failed"
                            base["notes"] += f" Download failed: {str(exc)[:300]}"
            manifest.append(base)
            audit.append({
                "fortune_rank": base["fortune_rank"],
                "firm_name": base["firm_name"],
                "target_report_year": base["target_report_year"],
                "status": base["status"],
                "error_type": "" if base["status"] in {"found", "no_10k_for_year", "no_cik_match"} else base["status"],
                "error_message": base["notes"] if base["status"] not in {"found"} else "",
                "sec_cik": base["sec_cik"],
                "sec_company_name": base["sec_company_name"],
                "sec_match_score": base["sec_match_score"],
                "sec_filing_url": base["sec_filing_url"],
                "local_report_path": base["local_report_path"],
                "attempted_at": collected_at,
            })
        print(f"rank={firm.fortune_rank} firm={firm.firm_name} match={company.title if company else 'NONE'} score={score:.2f} status={match_status}", flush=True)
    return manifest, audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect SEC 10-K report URLs/files for Fortune 2025 top companies.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--cache-dir", type=Path, default=DATA_ROOT / "sec_10k" / "cache")
    parser.add_argument("--rank-limit", type=int, default=100)
    parser.add_argument("--years", default=",".join(str(year) for year in DEFAULT_YEARS), help="Comma-separated reportDate years, e.g. 2025,2024,2023")
    parser.add_argument("--download", action="store_true", help="Download primary 10-K documents in addition to writing manifest URLs.")
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--refresh-downloads", action="store_true")
    parser.add_argument("--delay-seconds", type=float, default=0.15)
    parser.add_argument("--match-threshold", type=float, default=72.0)
    parser.add_argument("--user-agent", default="", help="SEC requires a descriptive User-Agent. Defaults to a repository research identifier.")
    args = parser.parse_args()
    args.years = [int(part.strip()) for part in args.years.split(",") if part.strip()]
    return args


def main() -> int:
    args = parse_args()
    manifest, audit = collect(args)
    write_csv(args.manifest, MANIFEST_FIELDS, manifest)
    write_csv(args.audit, AUDIT_FIELDS, audit)
    print(f"wrote {len(manifest)} rows to {args.manifest}")
    print(f"wrote {len(audit)} rows to {args.audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
