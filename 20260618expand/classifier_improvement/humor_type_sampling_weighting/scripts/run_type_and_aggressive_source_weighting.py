from _sampling_common import *
WEIGHTS=[('W100',1.0),('W25',0.25),('W50',0.50),('W75',0.75)]
def weights(rows,wendy_w): return [wendy_w if r['source']=='wendys_human_type' else 1.0 for r in rows]
def source_multi(rows, y, pred, setting):
    out=[]
    for src in sorted({r['source'] for r in rows}):
        idx=[i for i,r in enumerate(rows) if r['source']==src]
        out.append({'task':'type_4class','weight_setting':setting,'source':src,'n_rows':len(idx),**multi_metric(y[idx],pred[idx])})
    return out
def source_bin(rows, y, prob, pred, setting):
    out=[]
    for src in sorted({r['source'] for r in rows}):
        idx=[i for i,r in enumerate(rows) if r['source']==src]
        out.append({'task':'aggressive_detector','weight_setting':setting,'source':src,'n_rows':len(idx),**bin_metric(y[idx],prob[idx],pred[idx])})
    return out
def main():
    rows=read_csv(INPUT); type_rows=[]; pc_rows=[]; ag_rows=[]; th_rows=[]; src_rows=[]; leak_rows=[]
    for setting,ww in WEIGHTS:
        sw=weights(rows,ww)
        y,pred=split_oof_multi(rows,42,'balanced',sw); m=multi_metric(y,pred); pc=per_class(y,pred)
        type_rows.append({'weight_setting':setting,'batch1_weight':1.0,'wendys_weight':ww,'n_rows':len(rows),**m,'aggressive_f1':next(x['f1'] for x in pc if x['class_label']=='aggressive'),'aggressive_recall':next(x['recall'] for x in pc if x['class_label']=='aggressive'),'self_defeating_f1':next(x['f1'] for x in pc if x['class_label']=='self-defeating')})
        for r in pc: pc_rows.append({'weight_setting':setting,**r})
        src_rows += source_multi(rows,y,pred,setting)
        flag,lrows=leakage_multi(rows,42,'balanced',sw)
        for lr in lrows: leak_rows.append({'task':'type_4class','weight_setting':setting,**lr})
        yb,prob,predb=split_oof_bin(rows,42,'balanced',sw); am=bin_metric(yb,prob,predb)
        ag_rows.append({'weight_setting':setting,'batch1_weight':1.0,'wendys_weight':ww,'n_rows':len(rows),**am})
        th_rows += threshold_rows({'weight_setting':setting},yb,prob)
        src_rows += source_bin(rows,yb,prob,predb,setting)
        flag2,lrows2=leakage_bin(rows,42,'balanced',sw)
        for lr in lrows2: leak_rows.append({'task':'aggressive_detector','weight_setting':setting,**lr})
    write_csv(DATA/'source_weighting_type_metrics.csv',type_rows,['weight_setting','batch1_weight','wendys_weight','n_rows','macro_f1','weighted_f1','accuracy','aggressive_f1','aggressive_recall','self_defeating_f1'])
    write_csv(DATA/'source_weighting_type_per_class_metrics.csv',pc_rows,['weight_setting','class_label','support','precision','recall','f1'])
    write_csv(DATA/'source_weighting_aggressive_metrics.csv',ag_rows,['weight_setting','batch1_weight','wendys_weight','n_rows','pr_auc','roc_auc','f1','precision','recall'])
    write_csv(DATA/'source_weighting_aggressive_thresholds.csv',th_rows,['weight_setting','threshold','precision','recall','f1','meets_primary','meets_secondary'])
    write_csv(DATA/'source_weighting_source_aware_metrics.csv',src_rows,['task','weight_setting','source','n_rows','macro_f1','weighted_f1','accuracy','pr_auc','roc_auc','f1','precision','recall'])
    write_csv(DIAG/'source_weighting_leakage_diagnostic.csv',leak_rows,['task','weight_setting','class_label','diagnostic_token','feature','weight','rank_abs_weight','leakage_flag'])
    print('source weighting done')
if __name__=='__main__': main()
