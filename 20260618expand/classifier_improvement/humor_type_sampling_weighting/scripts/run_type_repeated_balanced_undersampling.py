from _sampling_common import *
import random

def sample_balanced(rows, seed):
    rng=random.Random(seed); groups=defaultdict(list)
    for r in rows: groups[r['humor_type']].append(r)
    out=[]
    for lab in LABELS: out += rng.sample(groups[lab], 39)
    rng.shuffle(out); return out

def source_metric(rows,y,pred,seed,cw):
    out=[]
    for src in sorted({r['source'] for r in rows}):
        idx=[i for i,r in enumerate(rows) if r['source']==src]
        m=multi_metric(y[idx],pred[idx])
        out.append({'seed':seed,'class_weight':str(cw),'source':src,'n_rows':len(idx),**m})
    return out

def main():
    DATA.mkdir(parents=True,exist_ok=True); DIAG.mkdir(parents=True,exist_ok=True)
    rows=read_csv(INPUT); byseed=[]; pc=[]; sm=[]; comp=[]; leaks=[]
    for seed in SEEDS:
        srows=sample_balanced(rows,seed); c=Counter(r['humor_type'] for r in srows); sc=Counter(r['source'] for r in srows)
        comp.append({'seed':seed,'total_rows':len(srows),'aggressive':c['aggressive'],'affiliative':c['affiliative'],'self_enhancing':c['self-enhancing'],'self_defeating':c['self-defeating'],'batch1_rows':sc['batch1_fortune100'],'wendys_rows':sc['wendys_human_type']})
        for cw in [None,'balanced']:
            y,p=split_oof_multi(srows,seed,cw); m=multi_metric(y,p); per=per_class(y,p)
            byseed.append({'seed':seed,'class_weight':str(cw),'n_rows':len(srows),**m,'aggressive_f1':next(x['f1'] for x in per if x['class_label']=='aggressive'),'self_defeating_f1':next(x['f1'] for x in per if x['class_label']=='self-defeating')})
            for r in per: pc.append({'seed':seed,'class_weight':str(cw),**r})
            sm += source_metric(srows,y,p,seed,cw)
            flag,lrows=leakage_multi(srows,seed,cw)
            for lr in lrows: leaks.append({'seed':seed,'class_weight':str(cw),**lr})
    summary=[]
    for cw in sorted({r['class_weight'] for r in byseed}):
        sub=[r for r in byseed if r['class_weight']==cw]
        for metric in ['macro_f1','weighted_f1','accuracy','aggressive_f1','self_defeating_f1']:
            vals=[float(r[metric]) for r in sub]
            summary.append({'class_weight':cw,'metric':metric,'mean':round(statistics.mean(vals),4),'std':round(statistics.stdev(vals),4),'n_seeds':len(vals)})
    write_csv(DATA/'type_balanced_undersampling_by_seed.csv',byseed,['seed','class_weight','n_rows','macro_f1','weighted_f1','accuracy','aggressive_f1','self_defeating_f1'])
    write_csv(DATA/'type_balanced_undersampling_summary.csv',summary,['class_weight','metric','mean','std','n_seeds'])
    write_csv(DATA/'type_balanced_undersampling_per_class_metrics.csv',pc,['seed','class_weight','class_label','support','precision','recall','f1'])
    write_csv(DATA/'type_balanced_undersampling_source_metrics.csv',sm,['seed','class_weight','source','n_rows','macro_f1','weighted_f1','accuracy'])
    write_csv(DIAG/'type_balanced_undersampling_leakage.csv',leaks,['seed','class_weight','class_label','diagnostic_token','feature','weight','rank_abs_weight','leakage_flag'])
    write_csv(DIAG/'type_balanced_undersampling_sample_composition.csv',comp,['seed','total_rows','aggressive','affiliative','self_enhancing','self_defeating','batch1_rows','wendys_rows'])
    print('type balanced done')
if __name__=='__main__': main()
