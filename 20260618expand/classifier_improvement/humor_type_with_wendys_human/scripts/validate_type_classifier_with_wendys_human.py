from __future__ import annotations
import csv, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]; BASE=ROOT/'20260618expand/classifier_improvement/humor_type_with_wendys_human'; DATA=BASE/'data'; DIAG=BASE/'diagnostics'; PRED=BASE/'predictions'
REQ=[DATA/'type_training_batch1_only.csv',DATA/'type_training_batch1_plus_wendys_human.csv',DIAG/'type_training_source_inventory.csv',DIAG/'type_training_label_distribution.csv',DIAG/'type_training_duplicate_diagnostics.csv',DIAG/'type_training_conflict_diagnostics.csv',DIAG/'type_training_exclusion_summary.csv',DATA/'type_model_comparison_metrics.csv',DATA/'type_model_per_class_metrics.csv',DATA/'type_model_source_aware_metrics.csv',DATA/'type_model_source_heldout_metrics.csv',DATA/'type_model_confusion_matrices.csv',PRED/'type_model_a_oof_predictions.csv',PRED/'type_model_b_oof_predictions.csv',DIAG/'type_model_top_features.csv',DIAG/'type_model_leakage_diagnostic.csv',DATA/'aggressive_detector_metrics.csv',DATA/'aggressive_detector_threshold_diagnostics.csv',DATA/'aggressive_detector_source_aware_metrics.csv',DATA/'aggressive_detector_source_heldout_metrics.csv',DATA/'aggressive_detector_confusion_matrices.csv',PRED/'aggressive_detector_oof_predictions.csv',DIAG/'aggressive_detector_top_features.csv',DIAG/'aggressive_detector_leakage_diagnostic.csv',DATA/'type_and_aggressive_model_summary.csv',DIAG/'validation_summary.csv']
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def count(rows):
    d={}
    for r in rows: d[r['humor_type']]=d.get(r['humor_type'],0)+1
    return d
def main():
    fails=[]
    for p in REQ:
        if not p.exists(): fails.append(f'missing {p.relative_to(ROOT)}')
    if not fails:
        b=read(DATA/'type_training_batch1_only.csv'); c=read(DATA/'type_training_batch1_plus_wendys_human.csv'); w=[r for r in c if r['source']=='wendys_human_type']
        cb,cw,cc=count(b),count(w),count(c)
        if len(b)!=648: fails.append(f'batch1 type rows expected 648 got {len(b)}')
        if len(w)!=278: fails.append(f'Wendy human type rows expected 278 got {len(w)}')
        if len(c)!=926: fails.append(f'combined type rows expected 926 got {len(c)}')
        if cb.get('aggressive')!=44: fails.append(f'batch1 aggressive expected 44 got {cb.get("aggressive")}')
        if cc.get('aggressive')!=139: fails.append(f'combined aggressive expected 139 got {cc.get("aggressive")}')
        if cb.get('self-defeating')!=24: fails.append(f'batch1 self-defeating expected 24 got {cb.get("self-defeating")}')
        if cc.get('self-defeating')!=39: fails.append(f'combined self-defeating expected 39 got {cc.get("self-defeating")}')
        inv=read(DIAG/'type_training_source_inventory.csv')
        if not any(r['source_file']=='slide/model_prediction_type_distribution' and r['usable_for_training']=='no' and r['raw_rows']=='564' for r in inv): fails.append('model-prediction 564 exclusion not documented')
        ex=read(DIAG/'type_training_exclusion_summary.csv')
        if not any(r['source']=='wendys_model_prediction' and r['row_number']=='564' for r in ex): fails.append('model-prediction 564 exclusion summary missing')
        if not read(DATA/'type_model_per_class_metrics.csv'): fails.append('per-class metrics empty')
        if not read(DATA/'aggressive_detector_threshold_diagnostics.csv'): fails.append('threshold diagnostics empty')
        if not read(DIAG/'type_model_leakage_diagnostic.csv') or not read(DIAG/'aggressive_detector_leakage_diagnostic.csv'): fails.append('leakage diagnostics empty')
    out=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
    for line in out.splitlines():
        path=line[3:] if len(line)>3 else line
        if path.startswith('data/raw/') or path.startswith('dashboard/data/') or path.startswith('.github/workflows/'): fails.append(f'forbidden modified path {line}')
    if fails:
        print('VALIDATION FAIL'); [print('- '+x) for x in fails]; return 1
    print('VALIDATION PASS'); print('batch1_rows=648'); print('wendys_rows=278'); print('combined_rows=926'); print('model_prediction_564_used=NO'); return 0
if __name__=='__main__': raise SystemExit(main())
