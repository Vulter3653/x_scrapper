from _leakage_common import *
import subprocess
REQ=[DIAG/'leakage_token_inventory.csv',DATA/'type_training_leakage_filtered_variants.csv',DIAG/'leakage_filtering_summary.csv',DATA/'aggressive_filtered_full_eval_summary.csv',DATA/'aggressive_filtered_full_eval_by_seed.csv',DATA/'aggressive_filtered_full_eval_thresholds.csv',DATA/'aggressive_filtered_full_eval_source_metrics.csv',DATA/'aggressive_filtered_full_eval_source_heldout.csv',DATA/'aggressive_filtered_full_eval_confusion_matrices.csv',PRED/'aggressive_filtered_full_eval_oof_predictions.csv',DIAG/'aggressive_filtered_full_eval_top_features.csv',DIAG/'aggressive_filtered_full_eval_leakage.csv',DIAG/'aggressive_filtered_full_eval_fold_diagnostics.csv',DATA/'type_filtered_metrics.csv',DATA/'type_filtered_per_class_metrics.csv',DATA/'type_filtered_source_metrics.csv',DATA/'type_filtered_source_heldout.csv',DATA/'type_filtered_confusion_matrices.csv',PRED/'type_filtered_oof_predictions.csv',DIAG/'type_filtered_top_features.csv',DIAG/'type_filtered_leakage.csv',DATA/'leakage_filtered_model_summary.csv',DATA/'aggressive_leakage_filtered_candidate_summary.csv',DATA/'type_leakage_filtered_candidate_summary.csv',DIAG/'validation_summary.csv']
def main():
    fails=[]
    for p in REQ:
        if not p.exists(): fails.append(f'missing {p.relative_to(ROOT)}')
    rows=read_csv(INPUT); c=Counter(r['humor_type'] for r in rows)
    if len(rows)!=926: fails.append('input rows !=926')
    if c['aggressive']!=139: fails.append('aggressive count !=139')
    if len(rows)-c['aggressive']!=787: fails.append('non-aggressive count !=787')
    if not fails:
        vr=read_csv(DATA/'type_training_leakage_filtered_variants.csv')[0]
        for col in ['text_original','text_mask_wendys_brand','text_mask_brand_product','text_mask_brand_product_competitor','text_mask_campaign_product','text_mask_all_leakage_groups']:
            if col not in vr: fails.append(f'missing variant {col}')
        fd=read_csv(DIAG/'aggressive_filtered_full_eval_fold_diagnostics.csv')
        if not fd or any(int(r['validation_full_rows'])<=0 or int(r['train_balanced_rows'])<=0 for r in fd): fails.append('fold diagnostics missing full validation/balanced train columns')
        if not any(r['check']=='model_prediction_564_rows_used' and r['status']=='NO' for r in read_csv(DIAG/'validation_summary.csv')): fails.append('model prediction exclusion missing')
    out=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
    for line in out.splitlines():
        path=line[3:] if len(line)>3 else line
        if path.startswith('data/raw/') or path.startswith('dashboard/data/') or path.startswith('.github/workflows/') or path.startswith('scripts/run_yearly_humor_backfill.py') or path.startswith('scripts/validate_yearly_humor_backfill_outputs.py'):
            fails.append(f'forbidden modified path: {line}')
    if fails:
        print('VALIDATION FAIL'); [print('- '+f) for f in fails]; return 1
    print('VALIDATION PASS'); print('input_rows=926'); print('aggressive_count=139'); print('non_aggressive_count=787'); print('model_prediction_564_used=NO'); return 0
if __name__=='__main__': raise SystemExit(main())
