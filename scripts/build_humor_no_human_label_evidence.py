#!/usr/bin/env python3
"""Build model-free evidence package from v1 full-chain results and v1-v2 A/B comparison.

No human labels are available at this stage. All outputs are:
  - Model-free descriptive statistics derived from the v1 operational baseline
  - Disagreement audit between v1 and v2 (disagreement ≠ error, only ≠ consensus)
  - Sensitivity summary for rare humor types (aggressive, self_defeating)

CONSTRAINTS (enforced by design, not just by comment):
  - Does not create human_label, gold_label, coder_label, or adjudicated_label.
  - Does not treat v1-v2 consensus as ground truth.
  - Does not reclassify the full 68k master using v2.
  - Does not modify raw data or full-chain outputs.
  - Does not alter v2 cue weights or thresholds (cue calibration requires human labels first).

Inputs:
  data/derived/humor/full_chain/humor_full_chain_master.csv
  data/audit/humor/evaluation/humor_type_v1_v2_comparison.csv
  data/audit/humor/evaluation/humor_type_v1_v2_summary.json
  data/derived/humor/evaluation/humor_type_human_review_priority_sample.csv

Outputs:
  data/derived/humor/evidence/humor_v1_model_free_overall_summary.csv
  data/derived/humor/evidence/humor_v1_model_free_company_summary.csv
  data/derived/humor/evidence/humor_v1_v2_disagreement_audit.csv
  data/derived/humor/evidence/humor_rare_class_sensitivity_summary.csv
  data/audit/humor/evidence/humor_no_human_label_evidence_manifest.json
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MASTER    = Path("data/derived/humor/full_chain/humor_full_chain_master.csv")
DEFAULT_COMPARISON = Path("data/audit/humor/evaluation/humor_type_v1_v2_comparison.csv")
DEFAULT_SUMMARY    = Path("data/audit/humor/evaluation/humor_type_v1_v2_summary.json")
DEFAULT_PRIORITY   = Path("data/derived/humor/evaluation/humor_type_human_review_priority_sample.csv")

DEFAULT_OUT_OVERALL    = Path("data/derived/humor/evidence/humor_v1_model_free_overall_summary.csv")
DEFAULT_OUT_COMPANY    = Path("data/derived/humor/evidence/humor_v1_model_free_company_summary.csv")
DEFAULT_OUT_DISAGREEMENT = Path("data/derived/humor/evidence/humor_v1_v2_disagreement_audit.csv")
DEFAULT_OUT_RARE       = Path("data/derived/humor/evidence/humor_rare_class_sensitivity_summary.csv")
DEFAULT_OUT_MANIFEST   = Path("data/audit/humor/evidence/humor_no_human_label_evidence_manifest.json")

# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------
OVERALL_FIELDS = ["metric", "value", "note"]

COMPANY_FIELDS = [
    "company_name", "source_x_handle",
    "total_posts", "humor_posts", "non_humor_posts", "ambiguous_posts",
    "humor_rate", "ambiguous_rate",
    "affiliative_count", "self_enhancing_count", "aggressive_count", "self_defeating_count",
    "aggressive_rate_among_humor", "self_defeating_rate_among_humor",
    "positive_count", "neutral_count", "negative_count",
    "positive_rate", "negative_rate",
]

DISAGREEMENT_FIELDS = [
    "analysis_type", "v1_label", "v2_label", "transition_type",
    "count", "share_of_total", "share_of_v1_label", "note",
]

RARE_FIELDS = [
    "metric", "source", "value", "interpretation",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_rate(numerator: int, denominator: int, decimals: int = 4) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, decimals)


def load_csv(path: Path, label: str) -> list[dict]:
    if not path.exists():
        print(f"ERROR: {label} not found: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print(f"ERROR: {label} has no header: {path}", file=sys.stderr)
            sys.exit(1)
        return list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# A. v1 model-free overall summary
# ---------------------------------------------------------------------------

def build_overall_summary(master: list[dict]) -> list[dict]:
    n = len(master)
    presence = Counter(r.get("humor_presence", "").strip() for r in master)
    htype    = Counter(r.get("humor_type", "").strip() for r in master)
    sent     = Counter(r.get("sentiment_label", "").strip() for r in master)

    humor_count     = presence.get("humor", 0)
    non_humor_count = presence.get("non_humor", 0)
    ambiguous_count = presence.get("ambiguous", 0)
    aggressive      = htype.get("aggressive", 0)
    self_defeating  = htype.get("self_defeating", 0)
    positive        = sent.get("positive", 0)
    negative        = sent.get("negative", 0)

    rows = [
        {"metric": "total_posts",              "value": n,                                "note": "All rows in full-chain master"},
        {"metric": "humor_posts",              "value": humor_count,                      "note": "humor_presence == humor"},
        {"metric": "non_humor_posts",          "value": non_humor_count,                  "note": "humor_presence == non_humor"},
        {"metric": "ambiguous_posts",          "value": ambiguous_count,                  "note": "humor_presence == ambiguous; deferred from type classification"},
        {"metric": "humor_rate",               "value": safe_rate(humor_count, n),        "note": "humor_posts / total_posts"},
        {"metric": "ambiguous_rate",           "value": safe_rate(ambiguous_count, n),    "note": "ambiguous_posts / total_posts"},
        {"metric": "affiliative_count",        "value": htype.get("affiliative", 0),      "note": "humor_type == affiliative"},
        {"metric": "self_enhancing_count",     "value": htype.get("self_enhancing", 0),   "note": "humor_type == self_enhancing"},
        {"metric": "aggressive_count",         "value": aggressive,                       "note": "humor_type == aggressive; exploratory only, no human label"},
        {"metric": "self_defeating_count",     "value": self_defeating,                   "note": "humor_type == self_defeating; exploratory only, no human label"},
        {"metric": "not_applicable_count",     "value": htype.get("not_applicable", 0),   "note": "humor_type == not_applicable (non-humor posts)"},
        {"metric": "ambiguous_or_review_count","value": htype.get("ambiguous_or_review", 0), "note": "humor_type == ambiguous_or_review (deferred)"},
        {"metric": "aggressive_rate",          "value": safe_rate(aggressive, n),         "note": "aggressive_count / total_posts; no human label — interpret as exploratory"},
        {"metric": "self_defeating_rate",      "value": safe_rate(self_defeating, n),     "note": "self_defeating_count / total_posts; no human label — interpret as exploratory"},
        {"metric": "positive_count",           "value": positive,                         "note": "sentiment_label == positive"},
        {"metric": "negative_count",           "value": negative,                         "note": "sentiment_label == negative"},
        {"metric": "neutral_count",            "value": sent.get("neutral", 0),           "note": "sentiment_label == neutral"},
        {"metric": "positive_sentiment_rate",  "value": safe_rate(positive, n),           "note": "positive_count / total_posts"},
        {"metric": "negative_sentiment_rate",  "value": safe_rate(negative, n),           "note": "negative_count / total_posts"},
        {"metric": "no_human_label",           "value": "true",                           "note": "No human-adjudicated labels exist. All humor type counts are v1 operational labels only."},
        {"metric": "gold_label_created",       "value": "false",                          "note": "v1-v2 consensus is NOT treated as gold label."},
    ]

    # Per-presence and per-type breakdown rows
    for val, cnt in sorted(presence.items()):
        rows.append({
            "metric": f"presence__{val}",
            "value":  cnt,
            "note":   f"humor_presence == {val!r}",
        })
    for val, cnt in sorted(htype.items()):
        if val not in ("affiliative", "self_enhancing", "aggressive", "self_defeating",
                       "not_applicable", "ambiguous_or_review"):
            rows.append({
                "metric": f"humor_type__{val}",
                "value":  cnt,
                "note":   f"humor_type == {val!r} (unlabelled bucket)",
            })
    for val, cnt in sorted(sent.items()):
        rows.append({
            "metric": f"sentiment__{val}",
            "value":  cnt,
            "note":   f"sentiment_label == {val!r}",
        })

    return rows


# ---------------------------------------------------------------------------
# B. v1 company-level summary
# ---------------------------------------------------------------------------

def build_company_summary(master: list[dict]) -> list[dict]:
    # Group by company_name; take first source_x_handle encountered per company
    by_company: dict[str, list[dict]] = defaultdict(list)
    handle_map: dict[str, str] = {}
    for r in master:
        cname = r.get("company_name", "").strip()
        if not cname:
            cname = "_unknown"
        by_company[cname].append(r)
        if cname not in handle_map:
            handle_map[cname] = r.get("source_x_handle", "").strip()

    output_rows = []
    for cname, rows in sorted(by_company.items()):
        n = len(rows)
        presence = Counter(r.get("humor_presence", "").strip() for r in rows)
        htype    = Counter(r.get("humor_type", "").strip() for r in rows)
        sent     = Counter(r.get("sentiment_label", "").strip() for r in rows)

        humor_posts    = presence.get("humor", 0)
        non_humor      = presence.get("non_humor", 0)
        ambiguous      = presence.get("ambiguous", 0)
        affiliative    = htype.get("affiliative", 0)
        self_enhancing = htype.get("self_enhancing", 0)
        aggressive     = htype.get("aggressive", 0)
        self_defeating = htype.get("self_defeating", 0)
        positive       = sent.get("positive", 0)
        neutral        = sent.get("neutral", 0)
        negative       = sent.get("negative", 0)

        output_rows.append({
            "company_name":               cname,
            "source_x_handle":            handle_map[cname],
            "total_posts":                n,
            "humor_posts":                humor_posts,
            "non_humor_posts":            non_humor,
            "ambiguous_posts":            ambiguous,
            "humor_rate":                 safe_rate(humor_posts, n),
            "ambiguous_rate":             safe_rate(ambiguous, n),
            "affiliative_count":          affiliative,
            "self_enhancing_count":       self_enhancing,
            "aggressive_count":           aggressive,
            "self_defeating_count":       self_defeating,
            "aggressive_rate_among_humor":    safe_rate(aggressive, humor_posts),
            "self_defeating_rate_among_humor": safe_rate(self_defeating, humor_posts),
            "positive_count":             positive,
            "neutral_count":              neutral,
            "negative_count":             negative,
            "positive_rate":              safe_rate(positive, n),
            "negative_rate":              safe_rate(negative, n),
        })

    return output_rows


# ---------------------------------------------------------------------------
# C. v1-v2 disagreement audit
# ---------------------------------------------------------------------------

def build_disagreement_audit(comparison: list[dict]) -> list[dict]:
    n = len(comparison)
    output_rows = []

    # 1. Transition-type summary
    transition_counts = Counter(r.get("transition_type", "").strip() for r in comparison)
    v1_per_transition: dict[str, Counter] = defaultdict(Counter)
    v2_per_transition: dict[str, Counter] = defaultdict(Counter)
    for r in comparison:
        tt  = r.get("transition_type", "").strip()
        v1l = r.get("v1_label", "").strip()
        v2l = r.get("v2_label", "").strip()
        v1_per_transition[tt][v1l] += 1
        v2_per_transition[tt][v2l] += 1

    for tt, cnt in sorted(transition_counts.items(), key=lambda x: -x[1]):
        output_rows.append({
            "analysis_type":    "transition_type_summary",
            "v1_label":         "",
            "v2_label":         "",
            "transition_type":  tt,
            "count":            cnt,
            "share_of_total":   safe_rate(cnt, n),
            "share_of_v1_label": "",
            "note": (
                "agreement" if tt == "same" else
                "v1 ambiguous resolved to humor type by v2" if tt == "resolved_to_humor" else
                "v1 ambiguous resolved to not_humor by v2" if tt == "resolved_to_not_humor" else
                "both v1 and v2 mark as ambiguous" if tt == "still_ambiguous" else
                "v1 humor, v2 not_humor" if tt == "humor_to_not_humor" else
                "v1 not_humor, v2 humor" if tt == "not_humor_to_humor" else
                "v1 humor, v2 ambiguous" if tt == "humor_to_ambiguous" else
                tt
            ),
        })

    # 2. v1_label × v2_label cross-tab
    cross: Counter = Counter()
    v1_totals: Counter = Counter()
    for r in comparison:
        v1l = r.get("v1_label", "").strip()
        v2l = r.get("v2_label", "").strip()
        cross[(v1l, v2l)] += 1
        v1_totals[v1l] += 1

    for (v1l, v2l), cnt in sorted(cross.items(), key=lambda x: (-x[1], x[0])):
        output_rows.append({
            "analysis_type":    "v1_v2_cross_tab",
            "v1_label":         v1l,
            "v2_label":         v2l,
            "transition_type":  "",
            "count":            cnt,
            "share_of_total":   safe_rate(cnt, n),
            "share_of_v1_label": safe_rate(cnt, v1_totals[v1l]),
            "note": "agreement" if v1l == v2l else "disagreement",
        })

    # 3. Ambiguous resolution breakdown
    ambig_rows = [r for r in comparison
                  if r.get("v1_label", "").strip() in {"ambiguous_or_review", "ambiguous_review"}]
    ambig_n = len(ambig_rows)
    ambig_v2 = Counter(r.get("v2_label", "").strip() for r in ambig_rows)
    for v2l, cnt in sorted(ambig_v2.items(), key=lambda x: -x[1]):
        output_rows.append({
            "analysis_type":    "ambiguous_resolution",
            "v1_label":         "ambiguous_or_review",
            "v2_label":         v2l,
            "transition_type":  "",
            "count":            cnt,
            "share_of_total":   safe_rate(cnt, n),
            "share_of_v1_label": safe_rate(cnt, ambig_n),
            "note": f"of {ambig_n} v1-ambiguous rows, v2 assigns {v2l!r}",
        })

    # 4. Rare-class specific transitions
    RARE_LABELS = {"aggressive", "self_defeating"}
    rare_transitions = [
        r for r in comparison
        if r.get("v1_label", "").strip() in RARE_LABELS
        or r.get("v2_label", "").strip() in RARE_LABELS
    ]
    rare_cross: Counter = Counter()
    for r in rare_transitions:
        v1l = r.get("v1_label", "").strip()
        v2l = r.get("v2_label", "").strip()
        rare_cross[(v1l, v2l)] += 1
    for (v1l, v2l), cnt in sorted(rare_cross.items(), key=lambda x: -x[1]):
        output_rows.append({
            "analysis_type":    "rare_class_transition",
            "v1_label":         v1l,
            "v2_label":         v2l,
            "transition_type":  "",
            "count":            cnt,
            "share_of_total":   safe_rate(cnt, n),
            "share_of_v1_label": safe_rate(cnt, v1_totals.get(v1l, 0)),
            "note": "exploratory only — no human label available",
        })

    # 5. Positive-humor-to-aggressive reclassification
    pos_to_aggr = [
        r for r in comparison
        if r.get("v1_label", "").strip() in {"affiliative", "self_enhancing"}
        and r.get("v2_label", "").strip() == "aggressive"
    ]
    if pos_to_aggr:
        output_rows.append({
            "analysis_type":    "type_shift_to_aggressive",
            "v1_label":         "affiliative_or_self_enhancing",
            "v2_label":         "aggressive",
            "transition_type":  "type_change",
            "count":            len(pos_to_aggr),
            "share_of_total":   safe_rate(len(pos_to_aggr), n),
            "share_of_v1_label": "",
            "note": "v1 positive humor reclassified as aggressive by v2; P3 priority review candidates",
        })

    return output_rows


# ---------------------------------------------------------------------------
# D. Rare class sensitivity summary
# ---------------------------------------------------------------------------

def build_rare_class_sensitivity(
    master: list[dict],
    ab_summary: dict,
    priority_sample: list[dict],
) -> list[dict]:
    # v1 counts from master
    htype = Counter(r.get("humor_type", "").strip() for r in master)
    v1_agg  = htype.get("aggressive", 0)
    v1_sd   = htype.get("self_defeating", 0)
    total_n = len(master)
    humor_n = sum(1 for r in master if r.get("humor_presence", "").strip() == "humor")

    # v2 counts from A/B summary
    rare_change = ab_summary.get("rare_class_change", {})
    v2_agg = rare_change.get("v2_aggressive", 0)
    v2_sd  = rare_change.get("v2_self_defeating", 0)
    agg_delta = rare_change.get("aggressive_delta", v2_agg - v1_agg)
    sd_delta  = rare_change.get("self_defeating_delta", v2_sd - v1_sd)
    ab_n = ab_summary.get("total_sample_rows", 0)

    # Priority sample counts
    p0_rare = [r for r in priority_sample if r.get("priority", "") == "P0"]
    p3_rows = [r for r in priority_sample if r.get("priority", "") == "P3"]

    CAUTION = "exploratory only — no human label; interpret as disagreement signal, not ground truth"

    rows: list[dict] = [
        # v1 baseline
        {"metric": "v1_aggressive_count",    "source": "full_chain_master (68k)",  "value": v1_agg,  "interpretation": f"v1 label; {safe_rate(v1_agg, total_n, 6)*100:.4f}% of all posts; {CAUTION}"},
        {"metric": "v1_self_defeating_count","source": "full_chain_master (68k)",  "value": v1_sd,   "interpretation": f"v1 label; {safe_rate(v1_sd, total_n, 6)*100:.4f}% of all posts; {CAUTION}"},
        {"metric": "v1_aggressive_rate_of_humor",    "source": "full_chain_master (68k)", "value": safe_rate(v1_agg, humor_n), "interpretation": f"aggressive_count / humor_posts ({humor_n}); {CAUTION}"},
        {"metric": "v1_self_defeating_rate_of_humor","source": "full_chain_master (68k)", "value": safe_rate(v1_sd, humor_n),  "interpretation": f"self_defeating_count / humor_posts ({humor_n}); {CAUTION}"},
        # v2 on A/B sample
        {"metric": "ab_sample_size",         "source": "v1_v2_comparison (A/B sample)", "value": ab_n, "interpretation": "stratified sample used for A/B test; not full 68k"},
        {"metric": "v2_aggressive_count_in_sample",     "source": "v2 A/B classification", "value": v2_agg,      "interpretation": f"v2 assigns aggressive to {v2_agg} of {ab_n} sample rows; {CAUTION}"},
        {"metric": "v2_self_defeating_count_in_sample", "source": "v2 A/B classification", "value": v2_sd,       "interpretation": f"v2 assigns self_defeating to {v2_sd} of {ab_n} sample rows; {CAUTION}"},
        {"metric": "aggressive_delta_in_sample",     "source": "v1 vs v2 (A/B sample)", "value": agg_delta,  "interpretation": f"v2 - v1 aggressive within sample; {'+' if agg_delta >= 0 else ''}{agg_delta}; {CAUTION}"},
        {"metric": "self_defeating_delta_in_sample", "source": "v1 vs v2 (A/B sample)", "value": sd_delta,   "interpretation": f"v2 - v1 self_defeating within sample; {'+' if sd_delta >= 0 else ''}{sd_delta}; {CAUTION}"},
        # Human review candidates
        {"metric": "P0_rare_humor_candidates",    "source": "human_review_priority_sample", "value": len(p0_rare), "interpretation": "v1 ambiguous → v2 aggressive or self_defeating; highest review priority"},
        {"metric": "P3_type_shift_candidates",    "source": "human_review_priority_sample", "value": len(p3_rows), "interpretation": "v1 affiliative/self_enhancing → v2 aggressive; pending human review"},
        {"metric": "total_rare_class_candidates", "source": "human_review_priority_sample", "value": len(p0_rare) + len(p3_rows), "interpretation": "P0 + P3 rows awaiting human adjudication"},
        # Constraints
        {"metric": "human_label_available",       "source": "this run",   "value": "false",  "interpretation": "No human labels exist. Rare class counts are v1/v2 operational labels only."},
        {"metric": "gold_label_created",          "source": "this run",   "value": "false",  "interpretation": "v1-v2 consensus is NOT used as gold label for rare classes."},
        {"metric": "cue_calibration_performed",   "source": "this run",   "value": "false",  "interpretation": "Cue/threshold adjustment requires human labels. Deferred."},
        {"metric": "v2_production_converted",     "source": "this run",   "value": "false",  "interpretation": "v2 remains a disagreement detector only. full-chain master unchanged."},
    ]
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build model-free humor evidence package (no human labels)."
    )
    parser.add_argument("--master",     type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--comparison", type=Path, default=DEFAULT_COMPARISON)
    parser.add_argument("--summary",    type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--priority",   type=Path, default=DEFAULT_PRIORITY)
    parser.add_argument("--out-overall",      type=Path, default=DEFAULT_OUT_OVERALL)
    parser.add_argument("--out-company",      type=Path, default=DEFAULT_OUT_COMPANY)
    parser.add_argument("--out-disagreement", type=Path, default=DEFAULT_OUT_DISAGREEMENT)
    parser.add_argument("--out-rare",         type=Path, default=DEFAULT_OUT_RARE)
    parser.add_argument("--out-manifest",     type=Path, default=DEFAULT_OUT_MANIFEST)
    args = parser.parse_args()

    print(f"Loading master:     {args.master}")
    master = load_csv(args.master, "full-chain master")
    print(f"  Rows: {len(master)}")

    print(f"Loading comparison: {args.comparison}")
    comparison = load_csv(args.comparison, "v1-v2 comparison")
    print(f"  Rows: {len(comparison)}")

    print(f"Loading AB summary: {args.summary}")
    if not args.summary.exists():
        print(f"ERROR: A/B summary not found: {args.summary}", file=sys.stderr)
        sys.exit(1)
    ab_summary = json.loads(args.summary.read_text(encoding="utf-8"))

    print(f"Loading priority sample: {args.priority}")
    priority_sample = load_csv(args.priority, "human review priority sample")
    print(f"  Rows: {len(priority_sample)}")

    print("\nBuilding A: overall summary...")
    overall_rows = build_overall_summary(master)
    n_overall = write_csv(args.out_overall, OVERALL_FIELDS, overall_rows)
    print(f"  Written {n_overall} rows → {args.out_overall}")

    print("Building B: company summary...")
    company_rows = build_company_summary(master)
    n_company = write_csv(args.out_company, COMPANY_FIELDS, company_rows)
    print(f"  Written {n_company} rows → {args.out_company}")

    print("Building C: disagreement audit...")
    disagreement_rows = build_disagreement_audit(comparison)
    n_disagreement = write_csv(args.out_disagreement, DISAGREEMENT_FIELDS, disagreement_rows)
    print(f"  Written {n_disagreement} rows → {args.out_disagreement}")

    print("Building D: rare class sensitivity summary...")
    rare_rows = build_rare_class_sensitivity(master, ab_summary, priority_sample)
    n_rare = write_csv(args.out_rare, RARE_FIELDS, rare_rows)
    print(f"  Written {n_rare} rows → {args.out_rare}")

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "created_at": created_at,
        "source_files": {
            "master":           str(args.master),
            "comparison":       str(args.comparison),
            "ab_summary":       str(args.summary),
            "priority_sample":  str(args.priority),
        },
        "output_files": {
            "overall_summary":     str(args.out_overall),
            "company_summary":     str(args.out_company),
            "disagreement_audit":  str(args.out_disagreement),
            "rare_class_sensitivity": str(args.out_rare),
        },
        "row_counts": {
            "master_rows":          len(master),
            "comparison_rows":      len(comparison),
            "priority_sample_rows": len(priority_sample),
            "overall_summary_rows": n_overall,
            "company_summary_rows": n_company,
            "disagreement_audit_rows": n_disagreement,
            "rare_class_summary_rows": n_rare,
        },
        "constraints": {
            "no_human_label":              True,
            "gold_label_created":          False,
            "coder_label_created":         False,
            "adjudicated_label_created":   False,
            "v1_v2_consensus_as_gold":     False,
            "v2_production_converted":     False,
            "full_chain_overwritten":      False,
            "raw_data_modified":           False,
            "cue_calibration_performed":   False,
        },
        "interpretation_notes": [
            "All humor type counts are v1 operational labels. No human ground truth exists.",
            "v1-v2 agreement rate (39.53%) is a consistency indicator, not an accuracy estimate.",
            "aggressive and self_defeating rare-class counts are exploratory. Do not report as validated.",
            "v2 is a disagreement detector / candidate generator, not a production classifier.",
            "Cue/threshold calibration must wait until human adjudication labels are available.",
        ],
    }

    args.out_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  Manifest → {args.out_manifest}")
    print(f"\nDone. Created at {created_at}")


if __name__ == "__main__":
    main()
