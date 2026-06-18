from _sampling_common import *
import random

def sample_balanced(rows, seed):
    rng=random.Random(seed); pos=[r for r in rows if r['humor_type']=='aggressive']; neg=[r for r in rows if r['humor_type']!='aggressive']; out=pos+rng.sample(neg,139); rng.shuffle(out); return out

def source_metric(rows,y,prob,pred,seed,cw):
    out=[]
    for src in sorted({r['source'] for r in rows}):
        idx=[i for i,r in enumerate(rows) if r['source']==src]
        out.append({'seed':seed,'class_weight':str(cw),'source':src,'n_rows':len(idx),**bin_metric(y[idx],prob[idx],pred[idx])})
    return out

def main():
    rows=read_csv(INPUT); byseed=[]; th=[]; sm=[]; comp=[]; leaks=[]
    for seed in SEEDS:
        srows=sample_balanced(rows,seed); y0=ag_y(srows); sc=Counter(r['source'] for r in srows)
        comp.append({'seed':seed,'total_rows':len(srows),'aggressive':int(y0.sum()),'other':int(len(y0)-y0.sum()),'batch1_rows':sc['batch1_fortune100'],'wendys_rows':sc['wendys_human_type']})
        for cw in [None,'balanced']:
            y,prob,pred=split_oof_bin(srows,seed,cw); m=bin_metric(y,prob,pred); byseed.append({'seed':seed,'class_weight':str(cw),'n_rows':len(srows),**m})
            th += threshold_rows({'seed':seed,'class_weight':str(cw)},y,prob); sm += source_metric(srows,y,prob,pred,seed,cw)
            flag,lrows=leakage_bin(srows,seed,cw)
            for lr in lrows: leaks.append({'seed':seed,'class_weight':str(cw),**lr})
    summary=[]
    for cw in sorted({r['class_weight'] for r in byseed}):
        sub=[r for r in byseed if r['class_weight']==cw]
        for metric in ['pr_auc','roc_auc','f1','precision','recall']:
            vals=[float(r[metric]) for r in sub]
            summary.append({'class_weight':cw,'metric':metric,'mean':round(statistics.mean(vals),4),'std':round(statistics.stdev(vals),4),'n_seeds':len(vals)})
    write_csv(DATA/'aggressive_balanced_undersampling_by_seed.csv',byseed,['seed','class_weight','n_rows','pr_auc','roc_auc','f1','precision','recall'])
    write_csv(DATA/'aggressive_balanced_undersampling_summary.csv',summary,['class_weight','metric','mean','std','n_seeds'])
    write_csv(DATA/'aggressive_balanced_undersampling_thresholds.csv',th,['seed','class_weight','threshold','precision','recall','f1','meets_primary','meets_secondary'])
    write_csv(DATA/'aggressive_balanced_undersampling_source_metrics.csv',sm,['seed','class_weight','source','n_rows','pr_auc','roc_auc','f1','precision','recall'])
    write_csv(DIAG/'aggressive_balanced_undersampling_leakage.csv',leaks,['seed','class_weight','class_label','diagnostic_token','feature','weight','rank_abs_weight','leakage_flag'])
    write_csv(DIAG/'aggressive_balanced_undersampling_sample_composition.csv',comp,['seed','total_rows','aggressive','other','batch1_rows','wendys_rows'])
    print('aggressive balanced done')
if __name__=='__main__': main()
