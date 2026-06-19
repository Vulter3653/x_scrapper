"""
merge_wendys_human_labels_v2.py

Wendy's human-coded labels (597건, 전원 실제 사람 코딩)을
training-label v2에 통합하고 분류기를 재훈련한다.

Source:
  20260615wendy's/data/wendys_h2_coder1_priority_dataset.csv
  - final_humor_source: human=99 / coder1=250 / coder2=248 (전원 인간 코딩)
  - 기존 combined template과 중복 없음 (0/597)
  - integrated corpus와 전량 일치 (597/597)

중요:
  - 기존 f945aca 결과(simple_ols_baseline_main/)를 덮어쓰지 않는다.
  - v2 결과는 simple_ols_baseline_main_v2/ 에 저장한다.
  - 수식, 방법, 통제변수 일체 변경 없음.

Type mapping (Wendy schema → combined template):
  aggressive     → 1
  affiliative    → 2
  self-enhancing → 3
  self-defeating → 4
  non_humor / '' → '' (blank)
"""

from __future__ import annotations

import csv
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

ROOT   = Path(__file__).resolve().parents[3]
CI     = ROOT / "20260618expand" / "classifier_improvement"
WENDY_SRC = ROOT / "20260615wendy's" / "data" / "wendys_h2_coder1_priority_dataset.csv"

COMBINED   = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template_combined.csv"
COMBINED_V2 = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template_combined_v2.csv"
CLASSIFIED = CI / "data" / "classified" / "fortune100_domain_adapted_humor_classification.csv"
INTEGRATED = (CI / "h1_presence_only" / "integrated_collected_corpus" / "data"
              / "integrated_h1_presence_classified_posts.csv")

# v2 OLS 출력 디렉토리
OLS_V2_DIR = ROOT / "20260618expand" / "ols_hypothesis_results" / "simple_ols_baseline_main_v2"

COMBINED_COLS = [
    "candidate_id", "sampling_stratum", "fortune_rank", "company_name",
    "source_x_handle", "tweet_id", "tweet_url", "created_at", "text",
    "total_engagement", "wendys_transfer_humor_presence", "wendys_transfer_humor_type",
    "full_chain_humor_presence", "full_chain_humor_type", "classifier_disagreement_flag",
    "human_humor_presence", "human_humor_type",
    "human_confidence", "human_notes", "reviewer_id", "review_status",
]

TYPE_STR_TO_CODE = {
    "aggressive":     "1",
    "affiliative":    "2",
    "self-enhancing": "3",
    "self-defeating": "4",
    "non_humor":      "",
    "":               "",
}

SOURCE_TO_REVIEWER = {
    "human":  "wendy_blind_human",
    "coder1": "wendy_coder1",
    "coder2": "wendy_coder2",
}


def main() -> None:
    print("=" * 65)
    print("merge_wendys_human_labels_v2")
    print("=" * 65)

    # ── 1. 기존 combined 로드 ──────────────────────────────────────────────
    with open(COMBINED, newline="", encoding="utf-8") as f:
        existing = list(csv.DictReader(f))
    existing_ids = {r["tweet_id"] for r in existing}
    print(f"\n기존 combined template: {len(existing)} rows")

    # ── 2. corpus 메타데이터 로드 (join 용) ───────────────────────────────
    with open(CLASSIFIED, newline="", encoding="utf-8") as f:
        classified = list(csv.DictReader(f))
    corpus_lookup = {r["tweet_id"]: r for r in classified}
    print(f"Corpus lookup: {len(corpus_lookup)} tweet_ids")

    # ── 3. Wendy's Source 로드 + 검증 ─────────────────────────────────────
    with open(WENDY_SRC, newline="", encoding="utf-8") as f:
        wendy_raw = list(csv.DictReader(f))

    print(f"\nWendy's source: {len(wendy_raw)} rows")
    print(f"  final_humor_source: {dict(Counter(r['final_humor_source'] for r in wendy_raw))}")
    print(f"  final_humor_binary: {dict(Counter(r['final_humor_binary'] for r in wendy_raw))}")
    print(f"  final_humor_type:   {dict(Counter(r['final_humor_type'] for r in wendy_raw))}")

    # 중복 확인
    dup_ids = {r["id"] for r in wendy_raw} & existing_ids
    if dup_ids:
        print(f"  경고: combined에 이미 있는 ID {len(dup_ids)}개 — 제외")
        wendy_raw = [r for r in wendy_raw if r["id"] not in existing_ids]

    # corpus 미포함 확인
    not_in_corpus = [r for r in wendy_raw if r["id"] not in corpus_lookup]
    if not_in_corpus:
        print(f"  경고: corpus에 없는 ID {len(not_in_corpus)}개 — 제외")
        wendy_raw = [r for r in wendy_raw if r["id"] in corpus_lookup]

    print(f"  중복제거 후 통합 가능: {len(wendy_raw)} rows")

    # ── 4. schema 변환 ─────────────────────────────────────────────────────
    new_rows = []
    for idx, r in enumerate(wendy_raw):
        tweet_id  = r["id"]
        corp      = corpus_lookup.get(tweet_id, {})

        presence_raw = r["final_humor_binary"]
        type_raw     = r["final_humor_type"]

        if presence_raw not in ("0", "1"):
            continue  # 유효하지 않은 presence 제외

        pres_code = presence_raw
        type_code = TYPE_STR_TO_CODE.get(type_raw, "")

        # presence=0 (비유머)이면 type은 항상 공란
        if pres_code == "0":
            type_code = ""

        reviewer = SOURCE_TO_REVIEWER.get(r["final_humor_source"], r["final_humor_source"])

        new_rows.append({
            "candidate_id":                 f"W{idx+1:05d}",
            "sampling_stratum":             "wendys_human_coded",
            "fortune_rank":                 corp.get("fortune_rank", ""),
            "company_name":                 corp.get("company_name", "Wendy's"),
            "source_x_handle":              corp.get("source_x_handle", "@Wendys"),
            "tweet_id":                     tweet_id,
            "tweet_url":                    r.get("tweet_url", corp.get("tweet_url", "")),
            "created_at":                   corp.get("created_at", ""),
            "text":                         r.get("text", corp.get("text", "")),
            "total_engagement":             r.get("engagement_total", corp.get("total_engagement", "")),
            "wendys_transfer_humor_presence": "",
            "wendys_transfer_humor_type":   "",
            "full_chain_humor_presence":    "",
            "full_chain_humor_type":        "",
            "classifier_disagreement_flag": "",
            "human_humor_presence":         pres_code,
            "human_humor_type":             type_code,
            "human_confidence":             "",
            "human_notes":                  "wendy_human_coded_v2",
            "reviewer_id":                  reviewer,
            "review_status":                "complete",
        })

    print(f"\n변환 완료: {len(new_rows)} rows")
    pres_new = Counter(r["human_humor_presence"] for r in new_rows)
    type_new = Counter(r["human_humor_type"] for r in new_rows if r["human_humor_type"])
    print(f"  presence: {dict(pres_new)}")
    print(f"  type:     {dict(type_new)}")

    # ── 5. Combined v2 생성 ────────────────────────────────────────────────
    merged_v2 = existing + new_rows
    valid_p_v2 = sum(1 for r in merged_v2 if r["human_humor_presence"] in ("0","1"))
    valid_t_v2 = sum(1 for r in merged_v2
                     if r["human_humor_presence"] == "1"
                     and r["human_humor_type"] in ("1","2","3","4"))

    type_dist_v2 = Counter(
        r["human_humor_type"] for r in merged_v2
        if r["human_humor_type"] in ("1","2","3","4")
    )

    print(f"\nCombined v2: {len(existing)} + {len(new_rows)} = {len(merged_v2)} rows")
    print(f"  유효 presence: {valid_p_v2}")
    print(f"  유효 type:     {valid_t_v2}")
    print(f"  type dist:     {dict(type_dist_v2)}")
    print(f"  (aggressive: {type_dist_v2.get('1','0')}, "
          f"affiliative: {type_dist_v2.get('2','0')}, "
          f"self_enhancing: {type_dist_v2.get('3','0')}, "
          f"self_defeating: {type_dist_v2.get('4','0')})")

    COMBINED_V2.parent.mkdir(parents=True, exist_ok=True)
    with open(COMBINED_V2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COMBINED_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(merged_v2)
    print(f"\n→ {COMBINED_V2.name} 저장 완료")

    # ── 6. 분류기 재훈련 + 재적용 ─────────────────────────────────────────
    print("\n[Step 6] apply_domain_adapted_classifier.py 재실행 (v2 template) ...")
    apply_script = CI / "scripts" / "apply_domain_adapted_classifier.py"
    result = subprocess.run(
        [sys.executable, str(apply_script),
         "--template", str(COMBINED_V2),
         "--input",    str(INTEGRATED)],
        cwd=str(ROOT),
        capture_output=False,
    )
    if result.returncode != 0:
        print("ERROR: apply_domain_adapted_classifier 실패")
        raise SystemExit(result.returncode)

    # ── 7. H1/H2/H3 데이터셋 재빌드 ──────────────────────────────────────
    print("\n[Step 7] build_h1h2h3_from_domain_adapted.py 재실행 ...")
    build_script = CI / "scripts" / "build_h1h2h3_from_domain_adapted.py"
    result = subprocess.run(
        [sys.executable, str(build_script)],
        cwd=str(ROOT),
        capture_output=False,
    )
    if result.returncode != 0:
        print("ERROR: build_h1h2h3 실패")
        raise SystemExit(result.returncode)

    # ── 8. v2 단순 OLS 분석 ───────────────────────────────────────────────
    print("\n[Step 8] v2 단순 OLS 분석 실행 ...")
    OLS_V2_DIR.mkdir(parents=True, exist_ok=True)
    ols_script = (ROOT / "20260618expand" / "ols_hypothesis_results"
                  / "simple_ols_baseline_main" / "run_simple_ols_baseline_main.py")

    # 동일 스크립트를 v2 출력 디렉토리로 실행하기 위해 임시 래퍼 생성
    _run_ols_v2(ols_script, COMBINED_V2, OLS_V2_DIR, ROOT)

    print("\n" + "=" * 65)
    print("merge_wendys_human_labels_v2 COMPLETE")
    print("=" * 65)
    print(f"\nv2 template  : {COMBINED_V2}")
    print(f"v2 OLS 결과  : {OLS_V2_DIR}")


def _run_ols_v2(ols_script: Path, template_v2: Path, out_dir: Path, root: Path) -> None:
    """
    run_simple_ols_baseline_main.py의 로직을 v2 템플릿 + v2 출력 디렉토리로 실행한다.
    원본 스크립트를 수정하지 않고 인라인으로 재실행한다.
    """
    import importlib.util, types

    # OUT 상수를 out_dir로 오버라이드하여 모듈 실행
    spec  = importlib.util.spec_from_file_location("ols_v2", str(ols_script))
    mod   = importlib.util.module_from_spec(spec)

    # 출력 경로 패치
    import importlib.util as ilu
    src = ols_script.read_text(encoding="utf-8")
    # OUT = Path(__file__).parent → out_dir 로 교체
    src = src.replace(
        "OUT  = Path(__file__).parent",
        f"OUT  = Path(r'{out_dir}')"
    )
    # TEMPLATE = CI / ... → COMBINED_V2 로 교체
    src = src.replace(
        "TEMPLATE    = CI / \"data\" / \"human_labeling_template\" / \"fortune100_human_labeling_template_combined.csv\"",
        f"TEMPLATE    = Path(r'{template_v2}')"
    )
    exec(compile(src, str(ols_script), "exec"),
         {"__file__": str(ols_script), "__name__": "__main__"})


if __name__ == "__main__":
    main()
