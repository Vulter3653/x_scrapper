"""
build_batch2_labeling_splits.py

Samples 1,500 additional Fortune Top 100 posts (batch 2) excluding all
tweet_ids already in batch 1, then splits them 500/500/500 for three coders.

All column names and guide text in Korean. Coded input values remain in English.

Outputs:
  data/labeling_candidates/fortune100_labeling_candidates_batch2.csv
  data/human_labeling_template/coder_splits/coder1_labeling_template_batch2.csv
  data/human_labeling_template/coder_splits/coder2_labeling_template_batch2.csv
  data/human_labeling_template/coder_splits/coder3_labeling_template_batch2.csv
  data/human_labeling_template/coder_splits/coder_assignment_summary_by_coder_batch2.csv
  data/human_labeling_template/coder_splits/coder_assignment_summary_by_stratum_batch2.csv
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / "20260618expand" / "classifier_improvement"

MASTER   = ROOT / "20260618expand" / "data" / "processed" / "fortune100_post_master.csv"
TRANSFER = ROOT / "20260618expand" / "model_transfer" / "data" / "classified" / \
           "fortune100_wendys_model_humor_classification.csv"
FULL_CHAIN = ROOT / "data" / "derived" / "humor" / "full_chain" / "humor_full_chain_master.csv"
BATCH1_CANDIDATES = CI / "data" / "labeling_candidates" / "fortune100_labeling_candidates.csv"

OUT_CANDIDATES = CI / "data" / "labeling_candidates" / "fortune100_labeling_candidates_batch2.csv"
SPLITS_DIR     = CI / "data" / "human_labeling_template" / "coder_splits"

RANDOM_SEED = 43          # batch1과 다른 seed
SAMPLE_SIZE = 1500
CODERS = ["coder1", "coder2", "coder3"]

# 영문 → 한국어 컬럼명 매핑
COL_MAP: dict[str, str] = {
    "candidate_id":                   "후보_ID",
    "sampling_stratum":               "표본_층화",
    "fortune_rank":                   "Fortune_순위",
    "company_name":                   "회사명",
    "source_x_handle":                "X_계정",
    "tweet_id":                       "트윗_ID",
    "tweet_url":                      "트윗_URL",
    "created_at":                     "작성일시",
    "text":                           "본문",
    "human_humor_presence":           "유머_존재여부",
    "human_humor_type":               "유머_유형",
    "assigned_coder":                 "배정_코더",
    "review_status":                  "검토_상태",
    "total_engagement":               "총_인게이지먼트",
    "log_total_engagement":           "로그_총_인게이지먼트",
    "wendys_transfer_humor_presence": "웬디스_유머_존재여부",
    "wendys_transfer_humor_score":    "웬디스_유머_점수",
    "wendys_transfer_humor_type":     "웬디스_유머_유형",
    "wendys_transfer_type_score":     "웬디스_유형_점수",
    "full_chain_humor_presence":      "풀체인_유머_존재여부",
    "full_chain_humor_type":          "풀체인_유머_유형",
    "classifier_disagreement_flag":   "분류기_불일치",
    "uncertainty_score":              "불확실성_점수",
}

PRIORITY_COLS_KO = [
    "후보_ID", "표본_층화", "Fortune_순위", "회사명", "X_계정",
    "트윗_ID", "트윗_URL", "작성일시", "본문",
    "유머_존재여부", "유머_유형",
    "배정_코더", "검토_상태",
]
REFERENCE_COLS_KO = [
    "총_인게이지먼트", "로그_총_인게이지먼트",
    "웬디스_유머_존재여부", "웬디스_유머_점수",
    "웬디스_유머_유형", "웬디스_유형_점수",
    "풀체인_유머_존재여부", "풀체인_유머_유형",
    "분류기_불일치", "불확실성_점수",
]


def safe_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def load_master() -> dict[str, dict]:
    with open(MASTER, newline="", encoding="utf-8-sig") as f:
        return {r["tweet_id"]: r for r in csv.DictReader(f)}


def load_transfer() -> dict[str, dict]:
    with open(TRANSFER, newline="", encoding="utf-8") as f:
        return {r["tweet_id"]: r for r in csv.DictReader(f)}


def load_full_chain() -> dict[str, dict]:
    if not FULL_CHAIN.exists():
        return {}
    with open(FULL_CHAIN, newline="", encoding="utf-8-sig") as f:
        return {r.get("tweet_id", ""): r for r in csv.DictReader(f) if r.get("tweet_id")}


def load_batch1_tids() -> set[str]:
    """
    Collects all tweet_ids already assigned in batch1.
    Reads both the candidates CSV (English columns) and
    the batch1 coder split files (Korean columns) to ensure
    no overlap regardless of which source was used.
    """
    tids: set[str] = set()
    # candidates CSV (영문 컬럼)
    if BATCH1_CANDIDATES.exists():
        with open(BATCH1_CANDIDATES, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                tids.add(r["tweet_id"])
    # batch1 coder split files (한국어 컬럼)
    for coder in CODERS:
        split_file = SPLITS_DIR / f"{coder}_labeling_template.csv"
        if split_file.exists():
            with open(split_file, newline="", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    tids.add(r.get("트윗_ID", ""))
    tids.discard("")
    return tids


def build_merged(master: dict, transfer: dict, full_chain: dict,
                 exclude_tids: set[str]) -> list[dict]:
    rows = []
    for tid, mr in master.items():
        if tid in exclude_tids:
            continue
        tr = transfer.get(tid, {})
        fc = full_chain.get(tid, {})

        presence_score = safe_float(tr.get("humor_presence_score", "0.5"))
        type_score     = safe_float(tr.get("humor_type_score", "0.0"))
        tr_presence    = tr.get("humor_presence", "")
        fc_presence    = fc.get("humor_presence", "")

        disagree = (
            (tr_presence == "1" and fc_presence == "non_humor") or
            (tr_presence == "0" and fc_presence == "humor")
        ) if fc_presence else False

        uncertainty = 1.0 - abs(2.0 * presence_score - 1.0) if tr_presence in ("0", "1") else 0.5

        rows.append({
            "tweet_id":                       tid,
            "fortune_rank":                   mr.get("fortune_rank", ""),
            "company_name":                   mr.get("company_name", ""),
            "source_x_handle":                mr.get("source_x_handle", ""),
            "tweet_url":                      mr.get("tweet_url", ""),
            "created_at":                     mr.get("created_at", ""),
            "text":                           mr.get("text", ""),
            "total_engagement":               mr.get("total_engagement", ""),
            "log_total_engagement":           mr.get("log_total_engagement", ""),
            "wendys_transfer_humor_presence": tr_presence,
            "wendys_transfer_humor_score":    f"{presence_score:.6f}",
            "wendys_transfer_humor_type":     tr.get("humor_type", ""),
            "wendys_transfer_type_score":     f"{type_score:.6f}",
            "full_chain_humor_presence":      fc_presence,
            "full_chain_humor_type":          fc.get("humor_type", ""),
            "classifier_disagreement_flag":   "1" if disagree else "0",
            "uncertainty_score":              f"{uncertainty:.6f}",
        })
    return rows


def stratified_sample(merged: list[dict], sample_size: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    by_id = {r["tweet_id"]: r for r in merged}
    selected: dict[str, str] = {}

    def add(pool: list[str], stratum: str, n: int) -> None:
        available = [t for t in pool if t not in selected]
        for tid in rng.sample(available, min(n, len(available))):
            selected[tid] = stratum

    transfer_agg  = [r["tweet_id"] for r in merged if r["wendys_transfer_humor_type"] == "aggressive"]
    # full_chain_aggressive는 batch1에서 소진 → 0개 예상
    fc_agg        = [r["tweet_id"] for r in merged if r["full_chain_humor_type"] == "aggressive"]
    disagreement  = [r["tweet_id"] for r in merged if r["classifier_disagreement_flag"] == "1"]
    unc_presence  = [r["tweet_id"] for r in merged
                     if 0.35 <= safe_float(r["wendys_transfer_humor_score"]) <= 0.65]
    unc_type      = [r["tweet_id"] for r in merged
                     if r["wendys_transfer_humor_presence"] == "1"
                     and safe_float(r["wendys_transfer_type_score"]) < 0.50]

    engs        = [(r["tweet_id"], safe_float(r["total_engagement"])) for r in merged]
    engs_sorted = sorted(engs, key=lambda x: -x[1])
    high_eng    = [t for t, _ in engs_sorted[:int(len(engs_sorted) * 0.05)]]
    low_eng     = [t for t, _ in engs_sorted[-int(len(engs_sorted) * 0.05):]]

    firms: dict[str, list[str]] = defaultdict(list)
    for r in merged:
        firms[r["company_name"]].append(r["tweet_id"])

    alloc = {
        "full_chain_aggressive_b2":       (fc_agg,       min(len(fc_agg), 120)),
        "wendys_transfer_aggressive_b2":  (transfer_agg, 200),
        "classifier_disagreement_b2":     (disagreement, 200),
        "humor_presence_uncertain_b2":    (unc_presence, 200),
        "type_uncertain_b2":              (unc_type,     100),
        "high_engagement_posts_b2":       (high_eng,     150),
        "low_engagement_posts_b2":        (low_eng,      100),
    }
    for stratum, (pool, n) in alloc.items():
        add(pool, stratum, n)

    # 기업 균형 (미선정 기업 우선)
    firm_pool = []
    for firm, tids in firms.items():
        avail = [t for t in tids if t not in selected]
        if avail:
            firm_pool.append(rng.choice(avail))
    add(firm_pool, "firm_balanced_sample_b2", len(firm_pool))

    remaining = sample_size - len(selected)
    if remaining > 0:
        rand_pool = [r["tweet_id"] for r in merged if r["tweet_id"] not in selected]
        add(rand_pool, "random_fortune_sample_b2", remaining)

    output = []
    for cid, (tid, stratum) in enumerate(selected.items(), start=1):
        r = by_id[tid]
        row = {"candidate_id": f"B{cid:05d}", "sampling_stratum": stratum}
        row.update(r)
        output.append(row)

    rng.shuffle(output)
    for cid, row in enumerate(output, start=1):
        row["candidate_id"] = f"B{cid:05d}"
    return output


def translate_row(row: dict) -> dict:
    return {COL_MAP.get(k, k): v for k, v in row.items()}


def build_ko_fieldnames() -> list[str]:
    priority_set = set(PRIORITY_COLS_KO)
    ref_present  = [c for c in REFERENCE_COLS_KO]
    return PRIORITY_COLS_KO + ref_present


def main() -> None:
    print("=== build_batch2_labeling_splits ===")

    print("  데이터 로드 중...")
    master     = load_master()
    transfer   = load_transfer()
    full_chain = load_full_chain()
    batch1_tids = load_batch1_tids()
    print(f"  master: {len(master)}, batch1 제외: {len(batch1_tids)}, "
          f"잔여 풀: {len(master) - len(batch1_tids)}")

    merged = build_merged(master, transfer, full_chain, batch1_tids)
    print(f"  merged (batch2 풀): {len(merged)}")

    candidates = stratified_sample(merged, SAMPLE_SIZE, RANDOM_SEED)
    print(f"  batch2 후보 선정: {len(candidates)}")

    from collections import Counter
    strata_dist = Counter(r["sampling_stratum"] for r in candidates)
    for s, n in sorted(strata_dist.items(), key=lambda x: -x[1]):
        print(f"    {s}: {n}")

    # 후보 CSV 저장 (영문 컬럼명, 기계 처리용)
    en_fields = [
        "candidate_id", "sampling_stratum", "fortune_rank", "company_name",
        "source_x_handle", "tweet_id", "tweet_url", "created_at", "text",
        "total_engagement", "log_total_engagement",
        "wendys_transfer_humor_presence", "wendys_transfer_humor_score",
        "wendys_transfer_humor_type", "wendys_transfer_type_score",
        "full_chain_humor_presence", "full_chain_humor_type",
        "classifier_disagreement_flag", "uncertainty_score",
    ]
    OUT_CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CANDIDATES.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=en_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(candidates)
    print(f"\n  후보 파일 → {OUT_CANDIDATES.name}")

    # coder split (한국어 컬럼명)
    rng = random.Random(RANDOM_SEED)
    rng.shuffle(candidates)
    splits = {
        "coder1": candidates[0:500],
        "coder2": candidates[500:1000],
        "coder3": candidates[1000:1500],
    }
    ko_fields = build_ko_fieldnames()
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)

    for coder, coder_rows in splits.items():
        out = SPLITS_DIR / f"{coder}_labeling_template_batch2.csv"
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=ko_fields, extrasaction="ignore")
            w.writeheader()
            for row in coder_rows:
                row_ko = translate_row(row)
                row_ko["유머_존재여부"] = ""
                row_ko["유머_유형"]     = ""
                row_ko["배정_코더"]     = coder
                row_ko["검토_상태"]     = "pending"
                w.writerow(row_ko)
        print(f"  {coder} batch2: {len(coder_rows)}행 → {out.name}")

    # 코더별 요약 (batch2)
    by_coder_path = SPLITS_DIR / "coder_assignment_summary_by_coder_batch2.csv"
    with by_coder_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=[
            "배정_코더", "배치", "행수", "고유_후보ID수", "고유_트윗ID수", "비고",
        ])
        w.writeheader()
        all_cids: set = set()
        all_tids: set = set()
        ov_cid = ov_tid = 0
        for coder, coder_rows in splits.items():
            cids_set = {r["candidate_id"] for r in coder_rows}
            tids_set = {r["tweet_id"]     for r in coder_rows}
            w.writerow({
                "배정_코더": coder, "배치": "batch2",
                "행수": len(coder_rows),
                "고유_후보ID수": len(cids_set),
                "고유_트윗ID수": len(tids_set),
                "비고": "",
            })
            ov_cid += len(cids_set & all_cids)
            ov_tid += len(tids_set & all_tids)
            all_cids |= cids_set
            all_tids |= tids_set
        w.writerow({
            "배정_코더": "합계", "배치": "batch2",
            "행수": 1500,
            "고유_후보ID수": len(all_cids),
            "고유_트윗ID수": len(all_tids),
            "비고": f"후보ID_중복={ov_cid} 트윗ID_중복={ov_tid}",
        })
    print(f"  코더별 요약(batch2) → {by_coder_path.name}")

    # 층화별 요약 (batch2)
    by_stratum_path = SPLITS_DIR / "coder_assignment_summary_by_stratum_batch2.csv"
    sc: dict[str, dict[str, int]] = defaultdict(lambda: {"coder1": 0, "coder2": 0, "coder3": 0})
    for coder, coder_rows in splits.items():
        for r in coder_rows:
            sc[r.get("sampling_stratum", "unknown")][coder] += 1
    with by_stratum_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["표본_층화", "코더1", "코더2", "코더3", "합계"])
        w.writeheader()
        for stratum, counts in sorted(sc.items()):
            w.writerow({
                "표본_층화": stratum,
                "코더1": counts["coder1"],
                "코더2": counts["coder2"],
                "코더3": counts["coder3"],
                "합계": sum(counts.values()),
            })
    print(f"  층화별 요약(batch2) → {by_stratum_path.name}")

    # Batch1과 중복 없음 확인
    b2_tids = {r["tweet_id"] for r in candidates}
    overlap = b2_tids & batch1_tids
    print(f"\n  batch1 ↔ batch2 트윗ID 중복: {len(overlap)}개 (0이어야 함)")
    assert len(overlap) == 0, "batch1과 batch2 중복 있음!"

    print("=== build_batch2_labeling_splits COMPLETE ===")


if __name__ == "__main__":
    main()
