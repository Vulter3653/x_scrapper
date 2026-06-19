"""
merge_coder3_batch2_v3.py

coder3 Batch2 (500행)을 training-label v3에 통합한다.
기존 combined (v1: 2,498행), v2 결과, simple OLS 결과는 수정하지 않는다.
v3 = combined_v2 (3,095행) + coder3 batch2 비중복 행

사용자 승인 전까지 classifier 재훈련 및 OLS 재실행 금지.

유머_존재여부=2 처리 원칙:
  - 오류로 처리하지 않는다.
  - audit 파일에 "reviewed_ambiguous"로 기록한다.
  - binary training (0/1 presence label)에는 포함하지 않는다.
  - type training에도 포함하지 않는다.
  - v3 파일에는 그대로 포함한다 (human_humor_presence='2').
"""
from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CI   = ROOT / "20260618expand" / "classifier_improvement"

COMBINED_V2   = CI / "data" / "human_labeling_template" / "fortune100_human_labeling_template_combined_v2.csv"
CODER3_BATCH2 = ROOT / "coder3_labeling_template_batch2.csv"

AUDIT_DIR = CI / "data" / "audit"
LABEL_DIR = CI / "data" / "human_labeling_template"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

OUT_AUDIT_MD  = AUDIT_DIR / "coder3_batch2_integration_audit.md"
OUT_AUDIT_CSV = AUDIT_DIR / "coder3_batch2_integration_audit.csv"
OUT_V3        = LABEL_DIR / "training_labels_v3_with_coder3_batch2.csv"
OUT_V3_DIST   = LABEL_DIR / "training_labels_v3_distribution.csv"
OUT_COMP      = LABEL_DIR / "v2_vs_v3_label_distribution_comparison.csv"

COMBINED_COLS = [
    "candidate_id", "sampling_stratum", "fortune_rank", "company_name",
    "source_x_handle", "tweet_id", "tweet_url", "created_at", "text",
    "total_engagement", "wendys_transfer_humor_presence", "wendys_transfer_humor_type",
    "full_chain_humor_presence", "full_chain_humor_type", "classifier_disagreement_flag",
    "human_humor_presence", "human_humor_type",
    "human_confidence", "human_notes", "reviewer_id", "review_status",
]

# 한국어 → 영어 컬럼 매핑
COL_MAP = {
    '후보_ID':      'candidate_id',
    '표본_층화':    'sampling_stratum',
    'Fortune_순위': 'fortune_rank',
    '회사명':       'company_name',
    'X_계정':       'source_x_handle',
    '트윗_ID':      'tweet_id',
    '트윗_URL':     'tweet_url',
    '작성일시':     'created_at',
    '본문':         'text',
    '유머_존재여부': 'human_humor_presence',
    '유머_유형':    'human_humor_type',
    '배정_코더':    'reviewer_id',
    '검토_상태':    'review_status',
    '총_인게이지먼트': 'total_engagement',
    '웬디스_유머_존재여부': 'wendys_transfer_humor_presence',
    '웬디스_유머_유형':     'wendys_transfer_humor_type',
    '풀체인_유머_존재여부': 'full_chain_humor_presence',
    '풀체인_유머_유형':     'full_chain_humor_type',
    '분류기_불일치': 'classifier_disagreement_flag',
}


def text_hash(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()[:12]


def normalize_tid(tid: str) -> str:
    try:
        return str(int(float(tid)))
    except (ValueError, TypeError):
        return str(tid).strip()


def compute_dist(rows: list[dict], label: str) -> dict:
    pres = [r.get("human_humor_presence", "") for r in rows]
    binary_elig = sum(1 for p in pres if p in ("0", "1"))
    p0 = sum(1 for p in pres if p == "0")
    p1 = sum(1 for p in pres if p == "1")
    p2 = sum(1 for p in pres if p == "2")
    type_rows = [r for r in rows
                 if r.get("human_humor_presence") == "1"
                 and r.get("human_humor_type") in ("1", "2", "3", "4")]
    tc = Counter(r["human_humor_type"] for r in type_rows)
    return {
        "version":                    label,
        "total_rows":                 len(rows),
        "binary_training_eligible":   binary_elig,
        "presence_0_non_humorous":    p0,
        "presence_1_humorous":        p1,
        "presence_2_ambiguous":       p2,
        "type_training_eligible":     len(type_rows),
        "type_1_aggressive":          tc.get("1", 0),
        "type_2_affiliative":         tc.get("2", 0),
        "type_3_self_enhancing":      tc.get("3", 0),
        "type_4_self_defeating":      tc.get("4", 0),
    }


def main() -> None:
    print("=" * 65)
    print("merge_coder3_batch2_v3  — integration audit only")
    print("  (classifier 재훈련은 사용자 승인 후 별도 실행)")
    print("=" * 65)

    # ── 1. v2 combined 로드 ────────────────────────────────────────────────
    with open(COMBINED_V2, newline="", encoding="utf-8") as f:
        v2_rows = list(csv.DictReader(f))
    print(f"\nv2 combined: {len(v2_rows):,} rows")

    v2_cids   = {r["candidate_id"] for r in v2_rows}
    v2_tids   = {normalize_tid(r["tweet_id"]) for r in v2_rows}
    v2_hashes = {text_hash(r["text"]) for r in v2_rows if r.get("text")}

    # ── 2. coder3 batch2 로드 ──────────────────────────────────────────────
    with open(CODER3_BATCH2, newline="", encoding="utf-8-sig") as f:
        raw_rows = list(csv.DictReader(f))
    print(f"coder3 batch2: {len(raw_rows):,} rows")

    pres_raw = Counter(r.get("유머_존재여부", "") for r in raw_rows)
    type_raw = Counter(r.get("유머_유형", "") for r in raw_rows if r.get("유머_유형"))
    print(f"  유머_존재여부: {dict(pres_raw)}")
    print(f"  유머_유형:     {dict(type_raw)}")

    # ── 3. 스키마 변환 ────────────────────────────────────────────────────
    coder3_mapped = []
    for r in raw_rows:
        mapped = {}
        for kor, eng in COL_MAP.items():
            mapped[eng] = r.get(kor, "")
        mapped["human_confidence"] = ""
        mapped["human_notes"]      = "coder3_batch2_v3"

        pres = str(mapped.get("human_humor_presence", "")).strip()
        mapped["human_humor_presence"] = pres

        typ = str(mapped.get("human_humor_type", "")).strip()
        # presence=1 이고 type이 1-4인 경우만 type label 유지
        if pres == "1" and typ in ("1", "2", "3", "4"):
            mapped["human_humor_type"] = typ
        else:
            mapped["human_humor_type"] = ""

        # review_status
        if pres == "2":
            mapped["review_status"] = "ambiguous"
        elif pres in ("0", "1"):
            mapped["review_status"] = "complete"

        # wendys_transfer_humor_presence: 0/1 정수
        wp = str(mapped.get("wendys_transfer_humor_presence", "")).strip()
        try:
            mapped["wendys_transfer_humor_presence"] = str(int(float(wp))) if wp else ""
        except ValueError:
            mapped["wendys_transfer_humor_presence"] = wp

        coder3_mapped.append(mapped)

    # ── 4. 중복 감지 ────────────────────────────────────────────────────────
    audit_rows = []
    to_add     = []
    cnt_dup_cid = cnt_dup_tid = cnt_dup_hash = 0

    for r in coder3_mapped:
        cid   = r["candidate_id"]
        tid   = normalize_tid(r["tweet_id"])
        thash = text_hash(r.get("text", ""))

        dup_flag   = "no_dup"
        dup_detail = ""

        if cid in v2_cids:
            dup_flag = "dup_candidate_id"
            dup_detail = f"candidate_id={cid} already in v2"
            cnt_dup_cid += 1
        elif tid in v2_tids:
            dup_flag = "dup_tweet_id"
            dup_detail = f"tweet_id={tid} already in v2"
            cnt_dup_tid += 1
        elif thash in v2_hashes:
            dup_flag = "dup_text_hash"
            dup_detail = f"text_hash={thash} already in v2"
            cnt_dup_hash += 1

        audit_rows.append({
            "candidate_id":          cid,
            "tweet_id":              tid,
            "text_hash":             thash,
            "human_humor_presence":  r["human_humor_presence"],
            "human_humor_type":      r["human_humor_type"],
            "dup_flag":              dup_flag,
            "dup_detail":            dup_detail,
        })

        if dup_flag == "no_dup":
            to_add.append(r)

    print(f"\n[중복 감지]")
    print(f"  candidate_id 중복: {cnt_dup_cid}")
    print(f"  tweet_id 중복:     {cnt_dup_tid}")
    print(f"  text_hash 중복:    {cnt_dup_hash}")
    print(f"  비중복 (추가):     {len(to_add)}")

    add_pres = Counter(r["human_humor_presence"] for r in to_add)
    add_type = Counter(r["human_humor_type"] for r in to_add if r["human_humor_type"])
    add_ambig = sum(1 for r in to_add if r["human_humor_presence"] == "2")

    print(f"\n추가 대상 presence: {dict(add_pres)}")
    print(f"추가 대상 type:     {dict(add_type)}")
    print(f"presence=2 (reviewed_ambiguous): {add_ambig}행 → v3에 포함, training 제외")

    # ── 5. v3 생성 ──────────────────────────────────────────────────────────
    v3_rows = v2_rows + to_add
    print(f"\nv3: {len(v2_rows):,} + {len(to_add)} = {len(v3_rows):,} rows")

    # ── 6. 파일 저장 ────────────────────────────────────────────────────────
    # audit CSV
    audit_fields = ["candidate_id", "tweet_id", "text_hash",
                    "human_humor_presence", "human_humor_type",
                    "dup_flag", "dup_detail"]
    with open(OUT_AUDIT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=audit_fields)
        w.writeheader()
        w.writerows(audit_rows)
    print(f"\n→ {OUT_AUDIT_CSV.name}")

    # v3 training label
    with open(OUT_V3, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COMBINED_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(v3_rows)
    print(f"→ {OUT_V3.name}")

    # 분포
    v2_dist = compute_dist(v2_rows, "v2")
    v3_dist = compute_dist(v3_rows, "v3")

    dist_fields = list(v3_dist.keys())
    with open(OUT_V3_DIST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=dist_fields)
        w.writeheader()
        w.writerow(v3_dist)
    print(f"→ {OUT_V3_DIST.name}")

    # v2 vs v3 비교
    comp_rows_out = []
    for k in dist_fields:
        if k == "version":
            continue
        v2v = v2_dist[k]
        v3v = v3_dist[k]
        comp_rows_out.append({
            "metric": k,
            "v2":     v2v,
            "v3":     v3v,
            "delta":  v3v - v2v if isinstance(v3v, int) else "",
        })
    with open(OUT_COMP, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "v2", "v3", "delta"])
        w.writeheader()
        w.writerows(comp_rows_out)
    print(f"→ {OUT_COMP.name}")

    # ── 7. audit MD ─────────────────────────────────────────────────────────
    dup_rows = [r for r in audit_rows if r["dup_flag"] != "no_dup"]

    dup_table = ""
    if dup_rows:
        dup_table = "| candidate_id | tweet_id | dup_flag | detail |\n"
        dup_table += "|:---|:---|:---|:---|\n"
        for row in dup_rows[:50]:
            dup_table += (f"| {row['candidate_id']} | {row['tweet_id']} "
                          f"| {row['dup_flag']} | {row['dup_detail']} |\n")
        if len(dup_rows) > 50:
            dup_table += f"\n*(나머지 {len(dup_rows)-50}건: audit CSV 참조)*\n"
    else:
        dup_table = "_중복 없음 — coder3 batch2 전량 신규 데이터_\n"

    md = f"""# coder3 Batch2 Integration Audit — training-label v3

생성일: 2026-06-19

## 입력 데이터
| 파일 | 행수 |
|:---|---:|
| v2 combined template (기준) | {len(v2_rows):,} |
| coder3 batch2 제출 | {len(raw_rows):,} |
| **v3 최종** | **{len(v3_rows):,}** |

## 중복 감지 (3중 기준)
| 중복 유형 | 건수 |
|:---|---:|
| candidate_id 중복 | {cnt_dup_cid} |
| tweet_id 중복 | {cnt_dup_tid} |
| text_hash 중복 | {cnt_dup_hash} |
| **비중복 (실제 추가)** | **{len(to_add)}** |

{dup_table}

## coder3 batch2 presence 분포
| 값 | 의미 | 건수 | training 처리 |
|:---|:---|---:|:---|
| 0 | non-humorous | {add_pres.get('0', 0)} | binary training 포함 |
| 1 | humorous | {add_pres.get('1', 0)} | binary + type training |
| 2 | reviewed ambiguous | {add_ambig} | **제외** (v3 파일에는 유지, human_notes='coder3_batch2_v3') |

## coder3 batch2 type 분포 (training 포함분, presence=1 & type 1-4)
| type | 유형 | 건수 |
|:---|:---|---:|
| 1 | aggressive | {add_type.get('1', 0)} |
| 2 | affiliative | {add_type.get('2', 0)} |
| 3 | self-enhancing | {add_type.get('3', 0)} |
| 4 | self-defeating | {add_type.get('4', 0)} |

## v2 → v3 변화 요약
| 지표 | v2 | v3 | 변화 |
|:---|---:|---:|---:|
| 총 행수 | {v2_dist['total_rows']:,} | {v3_dist['total_rows']:,} | **+{v3_dist['total_rows']-v2_dist['total_rows']}** |
| binary training eligible | {v2_dist['binary_training_eligible']:,} | {v3_dist['binary_training_eligible']:,} | +{v3_dist['binary_training_eligible']-v2_dist['binary_training_eligible']} |
| presence=0 (non-humorous) | {v2_dist['presence_0_non_humorous']:,} | {v3_dist['presence_0_non_humorous']:,} | +{v3_dist['presence_0_non_humorous']-v2_dist['presence_0_non_humorous']} |
| presence=1 (humorous) | {v2_dist['presence_1_humorous']:,} | {v3_dist['presence_1_humorous']:,} | +{v3_dist['presence_1_humorous']-v2_dist['presence_1_humorous']} |
| presence=2 (ambiguous) | {v2_dist['presence_2_ambiguous']} | {v3_dist['presence_2_ambiguous']} | +{v3_dist['presence_2_ambiguous']-v2_dist['presence_2_ambiguous']} |
| type training eligible | {v2_dist['type_training_eligible']:,} | {v3_dist['type_training_eligible']:,} | +{v3_dist['type_training_eligible']-v2_dist['type_training_eligible']} |
| aggressive (type=1) | {v2_dist['type_1_aggressive']} | {v3_dist['type_1_aggressive']} | +{v3_dist['type_1_aggressive']-v2_dist['type_1_aggressive']} |
| affiliative (type=2) | {v2_dist['type_2_affiliative']} | {v3_dist['type_2_affiliative']} | +{v3_dist['type_2_affiliative']-v2_dist['type_2_affiliative']} |
| self_enhancing (type=3) | {v2_dist['type_3_self_enhancing']} | {v3_dist['type_3_self_enhancing']} | +{v3_dist['type_3_self_enhancing']-v2_dist['type_3_self_enhancing']} |
| self_defeating (type=4) | {v2_dist['type_4_self_defeating']} | {v3_dist['type_4_self_defeating']} | +{v3_dist['type_4_self_defeating']-v2_dist['type_4_self_defeating']} |

## 다음 단계 (사용자 승인 후)
- [ ] v3 classifier 재훈련 (`apply_domain_adapted_classifier.py --template v3`)
- [ ] 전체 corpus 재분류
- [ ] H1/H2/H3 데이터셋 재빌드
- [ ] simple OLS baseline v3 실행

## 파일 목록
| 파일 | 위치 | 용도 |
|:---|:---|:---|
| `coder3_batch2_integration_audit.md` | data/audit/ | 이 문서 |
| `coder3_batch2_integration_audit.csv` | data/audit/ | 행별 중복 감지 상세 |
| `training_labels_v3_with_coder3_batch2.csv` | data/human_labeling_template/ | v3 training label 전체 |
| `training_labels_v3_distribution.csv` | data/human_labeling_template/ | v3 분포 요약 |
| `v2_vs_v3_label_distribution_comparison.csv` | data/human_labeling_template/ | v2↔v3 비교 |
"""

    OUT_AUDIT_MD.write_text(md, encoding="utf-8")
    print(f"→ {OUT_AUDIT_MD.name}")

    print("\n" + "=" * 65)
    print("완료 — 사용자 승인 대기")
    print("  ▷ 기존 v2 classifier 및 OLS 결과 유효")
    print("  ▷ 재훈련 시작 전 승인 필요")
    print("=" * 65)

    # 콘솔 요약
    print(f"\n[v2 → v3 핵심 변화]")
    print(f"  총 행: {v2_dist['total_rows']:,} → {v3_dist['total_rows']:,} (+{v3_dist['total_rows']-v2_dist['total_rows']})")
    print(f"  binary training: {v2_dist['binary_training_eligible']:,} → {v3_dist['binary_training_eligible']:,}")
    print(f"  type training:   {v2_dist['type_training_eligible']:,} → {v3_dist['type_training_eligible']:,}")
    print(f"  aggressive:      {v2_dist['type_1_aggressive']} → {v3_dist['type_1_aggressive']}")
    print(f"  affiliative:     {v2_dist['type_2_affiliative']} → {v3_dist['type_2_affiliative']}")
    print(f"  self_enhancing:  {v2_dist['type_3_self_enhancing']} → {v3_dist['type_3_self_enhancing']}")
    print(f"  self_defeating:  {v2_dist['type_4_self_defeating']} → {v3_dist['type_4_self_defeating']}")


if __name__ == "__main__":
    main()
