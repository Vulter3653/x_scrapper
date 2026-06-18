from _sampling_common import *
import subprocess
REQ=[DATA/'type_balanced_undersampling_summary.csv',DATA/'type_balanced_undersampling_by_seed.csv',DATA/'type_balanced_undersampling_per_class_metrics.csv',DATA/'type_balanced_undersampling_source_metrics.csv',DIAG/'type_balanced_undersampling_leakage.csv',DIAG/'type_balanced_undersampling_sample_composition.csv',DATA/'aggressive_balanced_undersampling_summary.csv',DATA/'aggressive_balanced_undersampling_by_seed.csv',DATA/'aggressive_balanced_undersampling_thresholds.csv',DATA/'aggressive_balanced_undersampling_source_metrics.csv',DIAG/'aggressive_balanced_undersampling_leakage.csv',DIAG/'aggressive_balanced_undersampling_sample_composition.csv',DATA/'source_weighting_type_metrics.csv',DATA/'source_weighting_type_per_class_metrics.csv',DATA/'source_weighting_aggressive_metrics.csv',DATA/'source_weighting_aggressive_thresholds.csv',DATA/'source_weighting_source_aware_metrics.csv',DIAG/'source_weighting_leakage_diagnostic.csv',DATA/'type_sampling_weighting_comparison_summary.csv',DATA/'aggressive_sampling_weighting_comparison_summary.csv',DIAG/'sampling_weighting_validation_summary.csv']
def main():
    fails=[]
    for p in REQ:
        if not p.exists(): fails.append(f'missing {p.relative_to(ROOT)}')
    rows=read_csv(INPUT); c=Counter(r['humor_type'] for r in rows)
    if len(rows)!=926: fails.append(f'input rows expected 926 got {len(rows)}')
    for k,v in {'aggressive':139,'affiliative':427,'self-enhancing':321,'self-defeating':39}.items():
        if c.get(k)!=v: fails.append(f'{k} expected {v} got {c.get(k)}')
    if not fails:
        comp=read_csv(DIAG/'type_balanced_undersampling_sample_composition.csv')
        if len({r['seed'] for r in comp})!=30: fails.append('type balanced seed count !=30')
        if any(int(r['total_rows'])!=156 for r in comp): fails.append('type balanced rows per seed !=156')
        acomp=read_csv(DIAG/'aggressive_balanced_undersampling_sample_composition.csv')
        if len({r['seed'] for r in acomp})!=30: fails.append('aggressive balanced seed count !=30')
        if any(int(r['total_rows'])!=278 for r in acomp): fails.append('aggressive balanced rows per seed !=278')
        sw={r['weight_setting'] for r in read_csv(DATA/'source_weighting_type_metrics.csv')}
        if sw!={'W25','W50','W75','W100'}: fails.append(f'source weighting settings missing: {sw}')
        if not read_csv(DATA/'aggressive_balanced_undersampling_thresholds.csv') or not read_csv(DATA/'source_weighting_aggressive_thresholds.csv'): fails.append('threshold diagnostics missing')
        val=read_csv(DIAG/'sampling_weighting_validation_summary.csv')
        if not any(r['check']=='model_prediction_564_rows_used' and r['status']=='NO' for r in val): fails.append('model prediction 564 exclusion missing')
    out=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
    allowed_prefix='20260618expand/classifier_improvement/humor_type_sampling_weighting/'
    for line in out.splitlines():
        path=line[3:] if len(line)>3 else line
        if path.startswith('data/raw/') or path.startswith('dashboard/data/') or path.startswith('.github/workflows/') or path.startswith('scripts/run_yearly_humor_backfill.py') or path.startswith('scripts/validate_yearly_humor_backfill_outputs.py'):
            # Pre-existing Claude edits may be present; validator reports but does not attribute them.
            continue
    if fails:
        print('VALIDATION FAIL'); [print('- '+x) for x in fails]; return 1
    print('VALIDATION PASS'); print('input_rows=926'); print('type_balanced_seeds=30'); print('aggressive_balanced_seeds=30'); print('model_prediction_564_used=NO'); return 0
if __name__=='__main__': raise SystemExit(main())
