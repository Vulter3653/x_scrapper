from _sampling_common import *
BASELINE=ROOT/'20260618expand/classifier_improvement/humor_type_with_wendys_human/data'
def rows(p): return read_csv(p)
def mean_lookup(p, cw, metric):
    for r in rows(p):
        if r.get('class_weight')==cw and r.get('metric')==metric: return r
    return {'mean':'','std':''}
def leak_flag(path, **filters):
    vals=[]
    for r in rows(path):
        if all(r.get(k)==v for k,v in filters.items()): vals.append(r.get('leakage_flag','PASS'))
    return 'FAIL' if 'FAIL' in vals else ('WARN' if 'WARN' in vals else 'PASS')
def main():
    type_base=rows(BASELINE/'type_model_comparison_metrics.csv'); type_pc=rows(BASELINE/'type_model_per_class_metrics.csv')
    ag_base=rows(BASELINE/'aggressive_detector_metrics.csv')
    out_t=[]; out_a=[]
    for r in type_base:
        out_t.append({'method':r['model_id'],'macro_f1':r['macro_f1'],'macro_f1_std':'','weighted_f1':r['weighted_f1'],'accuracy':r['accuracy'],'aggressive_f1':next(x['f1'] for x in type_pc if x['model_id']==r['model_id'] and x['class_label']=='aggressive' and x['eval_scope']=='all_training_rows'),'self_defeating_f1':next(x['f1'] for x in type_pc if x['model_id']==r['model_id'] and x['class_label']=='self-defeating' and x['eval_scope']=='all_training_rows'),'leakage_flag':'FAIL' if r['model_id'].endswith('wendys_human') else 'baseline','candidate_status':'baseline'})
    for cw in ['None','balanced']:
        out_t.append({'method':'balanced_undersampling_'+cw,'macro_f1':mean_lookup(DATA/'type_balanced_undersampling_summary.csv',cw,'macro_f1')['mean'],'macro_f1_std':mean_lookup(DATA/'type_balanced_undersampling_summary.csv',cw,'macro_f1')['std'],'weighted_f1':mean_lookup(DATA/'type_balanced_undersampling_summary.csv',cw,'weighted_f1')['mean'],'accuracy':mean_lookup(DATA/'type_balanced_undersampling_summary.csv',cw,'accuracy')['mean'],'aggressive_f1':mean_lookup(DATA/'type_balanced_undersampling_summary.csv',cw,'aggressive_f1')['mean'],'self_defeating_f1':mean_lookup(DATA/'type_balanced_undersampling_summary.csv',cw,'self_defeating_f1')['mean'],'leakage_flag':leak_flag(DIAG/'type_balanced_undersampling_leakage.csv',class_weight=cw),'candidate_status':'diagnostic_only_balanced_sampling'})
    for r in rows(DATA/'source_weighting_type_metrics.csv'):
        flag=leak_flag(DIAG/'source_weighting_leakage_diagnostic.csv',task='type_4class',weight_setting=r['weight_setting'])
        cand='source_weighted_candidate_only' if float(r['macro_f1'])>float(out_t[0]['macro_f1']) and float(r['aggressive_f1'])>float(out_t[0]['aggressive_f1']) and flag!='FAIL' else 'no_candidate_retain_baseline'
        out_t.append({'method':'source_weighting_'+r['weight_setting'],'macro_f1':r['macro_f1'],'macro_f1_std':'','weighted_f1':r['weighted_f1'],'accuracy':r['accuracy'],'aggressive_f1':r['aggressive_f1'],'self_defeating_f1':r['self_defeating_f1'],'leakage_flag':flag,'candidate_status':cand})
    for r in ag_base:
        out_a.append({'method':r['model_id'],'pr_auc':r['pr_auc'],'pr_auc_std':'','f1':r['f1'],'precision':r['precision'],'recall':r['recall'],'primary_or_secondary_threshold':'baseline','leakage_flag':'FAIL' if r['model_id'].endswith('wendys_human') else 'baseline','candidate_status':'baseline'})
    for cw in ['None','balanced']:
        out_a.append({'method':'balanced_undersampling_'+cw,'pr_auc':mean_lookup(DATA/'aggressive_balanced_undersampling_summary.csv',cw,'pr_auc')['mean'],'pr_auc_std':mean_lookup(DATA/'aggressive_balanced_undersampling_summary.csv',cw,'pr_auc')['std'],'f1':mean_lookup(DATA/'aggressive_balanced_undersampling_summary.csv',cw,'f1')['mean'],'precision':mean_lookup(DATA/'aggressive_balanced_undersampling_summary.csv',cw,'precision')['mean'],'recall':mean_lookup(DATA/'aggressive_balanced_undersampling_summary.csv',cw,'recall')['mean'],'primary_or_secondary_threshold':'yes' if any(r['class_weight']==cw and (r['meets_primary']=='yes' or r['meets_secondary']=='yes') for r in rows(DATA/'aggressive_balanced_undersampling_thresholds.csv')) else 'no','leakage_flag':leak_flag(DIAG/'aggressive_balanced_undersampling_leakage.csv',class_weight=cw),'candidate_status':'diagnostic_only_balanced_sampling'})
    for r in rows(DATA/'source_weighting_aggressive_metrics.csv'):
        flag=leak_flag(DIAG/'source_weighting_leakage_diagnostic.csv',task='aggressive_detector',weight_setting=r['weight_setting']); thresh='yes' if any(x['weight_setting']==r['weight_setting'] and (x['meets_primary']=='yes' or x['meets_secondary']=='yes') for x in rows(DATA/'source_weighting_aggressive_thresholds.csv')) else 'no'
        cand='aggressive_source_weighted_candidate_only' if float(r['pr_auc'])>float(out_a[0]['pr_auc']) and float(r['f1'])>float(out_a[0]['f1']) and thresh=='yes' and flag!='FAIL' else 'no_candidate_retain_baseline'
        out_a.append({'method':'source_weighting_'+r['weight_setting'],'pr_auc':r['pr_auc'],'pr_auc_std':'','f1':r['f1'],'precision':r['precision'],'recall':r['recall'],'primary_or_secondary_threshold':thresh,'leakage_flag':flag,'candidate_status':cand})
    write_csv(DATA/'type_sampling_weighting_comparison_summary.csv',out_t,['method','macro_f1','macro_f1_std','weighted_f1','accuracy','aggressive_f1','self_defeating_f1','leakage_flag','candidate_status'])
    write_csv(DATA/'aggressive_sampling_weighting_comparison_summary.csv',out_a,['method','pr_auc','pr_auc_std','f1','precision','recall','primary_or_secondary_threshold','leakage_flag','candidate_status'])
    write_csv(DIAG/'sampling_weighting_validation_summary.csv',[{'check':'model_prediction_564_rows_used','status':'NO'},{'check':'integrated_corpus_reclassification','status':'NOT_RUN'},{'check':'h1_h2_h3_regression','status':'NOT_RUN'},{'check':'yearly_backfill_files','status':'NOT_TOUCHED_BY_CODEX'}],['check','status'])
    print('summary done')
if __name__=='__main__': main()
