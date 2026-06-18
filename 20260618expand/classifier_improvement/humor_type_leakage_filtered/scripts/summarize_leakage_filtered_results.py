from _leakage_common import *
def rows(p): return read_csv(p)
def thresh_ok(variant): return any(r['variant']==variant and (r['meets_primary']=='yes' or r['meets_secondary']=='yes') for r in rows(DATA/'aggressive_filtered_full_eval_thresholds.csv'))
def main():
    ag=rows(DATA/'aggressive_filtered_full_eval_summary.csv'); ty=rows(DATA/'type_filtered_metrics.csv'); out=[]; agc=[]; tyc=[]
    out.append({'family':'aggressive_baseline_b','variant':'baseline_b','primary_metric':'pr_auc','value':0.4356,'f1':0.4474,'leakage_flag':'FAIL','candidate_status':'retain_baseline'})
    for r in ag:
        cand='aggressive_leakage_filtered_candidate_only' if float(r['pr_auc'])>=0.40 and float(r['f1'])>=0.40 and thresh_ok(r['variant']) and r['leakage_flag']!='FAIL' else 'diagnostic_only_no_candidate'
        agc.append({'variant':r['variant'],'pr_auc':r['pr_auc'],'f1':r['f1'],'precision':r['precision'],'recall':r['recall'],'threshold_condition_met':'yes' if thresh_ok(r['variant']) else 'no','leakage_flag':r['leakage_flag'],'candidate_status':cand})
        out.append({'family':'aggressive_filtered','variant':r['variant'],'primary_metric':'pr_auc','value':r['pr_auc'],'f1':r['f1'],'leakage_flag':r['leakage_flag'],'candidate_status':cand})
    out.append({'family':'type_baseline_b','variant':'baseline_b','primary_metric':'macro_f1','value':0.4194,'f1':'','leakage_flag':'FAIL','candidate_status':'retain_baseline'})
    for r in ty:
        cand='type_leakage_filtered_candidate_only' if float(r['macro_f1'])>=0.39 and float(r['aggressive_f1'])>=0.40 and float(r['self_defeating_f1'])>=0.10 and r['leakage_flag']!='FAIL' else 'diagnostic_only_no_candidate'
        tyc.append({'variant':r['variant'],'macro_f1':r['macro_f1'],'aggressive_f1':r['aggressive_f1'],'self_defeating_f1':r['self_defeating_f1'],'leakage_flag':r['leakage_flag'],'candidate_status':cand})
        out.append({'family':'type_filtered','variant':r['variant'],'primary_metric':'macro_f1','value':r['macro_f1'],'f1':r['aggressive_f1'],'leakage_flag':r['leakage_flag'],'candidate_status':cand})
    write_csv(DATA/'leakage_filtered_model_summary.csv',out,['family','variant','primary_metric','value','f1','leakage_flag','candidate_status'])
    write_csv(DATA/'aggressive_leakage_filtered_candidate_summary.csv',agc,['variant','pr_auc','f1','precision','recall','threshold_condition_met','leakage_flag','candidate_status'])
    write_csv(DATA/'type_leakage_filtered_candidate_summary.csv',tyc,['variant','macro_f1','aggressive_f1','self_defeating_f1','leakage_flag','candidate_status'])
    write_csv(DIAG/'validation_summary.csv',[{'check':'model_prediction_564_rows_used','status':'NO'},{'check':'integrated_corpus_reclassification','status':'NOT_RUN'},{'check':'h1_h2_h3_regression','status':'NOT_RUN'},{'check':'data_raw_dashboard_workflow_yearly_backfill','status':'NOT_MODIFIED_BY_CODEX'}],['check','status'])
    print('summary built')
if __name__=='__main__': main()
