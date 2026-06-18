from _leakage_common import *
TEXTCOL={'original_text':'text_original','mask_wendys_brand':'text_mask_wendys_brand','mask_brand_product':'text_mask_brand_product','mask_brand_product_competitor':'text_mask_brand_product_competitor','mask_campaign_product':'text_mask_campaign_product','mask_all_leakage_groups':'text_mask_all_leakage_groups'}
def eval_variant(rows,variant,seed):
    col=TEXTCOL[variant]; X=[prep(r[col]) for r in rows]; y=y_ag(rows); prob=np.zeros(len(y)); pred=np.zeros(len(y),int); cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=seed); rng=random.Random(seed)
    fold_rows=[]
    for fold,(tr,te) in enumerate(cv.split(X,y),1):
        pos=[i for i in tr if y[i]==1]; neg=[i for i in tr if y[i]==0]; samp=pos+rng.sample(neg,len(pos)); rng.shuffle(samp)
        m=make_bin(seed); m.fit([X[i] for i in samp], y[samp]); p=m.predict_proba([X[i] for i in te])[:,1]; prob[te]=p; pred[te]=(p>=.5).astype(int)
        fold_rows.append({'variant':variant,'seed':seed,'fold':fold,'train_full_rows':len(tr),'train_balanced_rows':len(samp),'train_positive_rows':len(pos),'train_negative_sampled_rows':len(pos),'validation_full_rows':len(te),'validation_positive_rows':int(y[te].sum()),'validation_negative_rows':int(len(te)-y[te].sum())})
    return y,prob,pred,fold_rows
def source_metrics(rows,variant,seed,y,prob,pred):
    out=[]
    for src in sorted({r['source'] for r in rows}):
        idx=[i for i,r in enumerate(rows) if r['source']==src]
        out.append({'variant':variant,'seed':seed,'source':src,'n_rows':len(idx),**bin_metric(y[idx],prob[idx],pred[idx])})
    return out
def heldout(rows,variant):
    col=TEXTCOL[variant]; b=[r for r in rows if r['source']=='batch1_fortune100']; w=[r for r in rows if r['source']=='wendys_human_type']; out=[]
    for name,tr,te in [('train_batch1_test_wendys',b,w),('train_wendys_test_batch1',w,b)]:
        m=make_bin(42); m.fit([prep(r[col]) for r in tr], y_ag(tr)); y=y_ag(te); p=m.predict_proba([prep(r[col]) for r in te])[:,1]; pr=(p>=.5).astype(int); out.append({'variant':variant,'eval_scope':name,'n_rows':len(te),**bin_metric(y,p,pr)})
    return out
def feature_leak(rows,variant):
    col=TEXTCOL[variant]; m=make_bin(42); m.fit([prep(r[col]) for r in rows],y_ag(rows)); flag,lr=leakage_from_model(m,True); names=[]
    for n,t in m.named_steps['vec'].transformer_list: names += [f'{n}__{x}' for x in t.get_feature_names_out()]
    co=m.named_steps['clf'].coef_[0]; top=[{'variant':variant,'rank':i+1,'feature':names[idx],'weight':round(float(co[idx]),6)} for i,idx in enumerate(np.argsort(co)[-50:][::-1])]
    for r in lr: r['variant']=variant
    return flag,lr,top
def main():
    rows=read_csv(DATA/'type_training_leakage_filtered_variants.csv'); summ=[]; by=[]; th=[]; src=[]; held=[]; cm=[]; predrows=[]; leaks=[]; tops=[]; folddiag=[]
    for variant in TEXTCOL:
        seed_metrics=[]
        for seed in SEEDS:
            y,p,pr,fd=eval_variant(rows,variant,seed); m=bin_metric(y,p,pr); seed_metrics.append(m); by.append({'variant':variant,'seed':seed,'n_rows':len(rows),'positive_count':int(y.sum()),'negative_count':int(len(y)-y.sum()),**m}); th+=thresholds({'variant':variant,'seed':seed},y,p); src+=source_metrics(rows,variant,seed,y,p,pr); folddiag+=fd
            c=confusion_matrix(y,pr,labels=[0,1]); cm += [{'variant':variant,'seed':seed,'actual_label':['non_aggressive','aggressive'][i],'predicted_label':['non_aggressive','aggressive'][j],'count':int(c[i,j])} for i in range(2) for j in range(2)]
            for r,yy,pp,rr in zip(rows,y,p,pr): predrows.append({'variant':variant,'seed':seed,'row_id':r['row_id'],'source':r['source'],'true_aggressive':int(yy),'oof_probability':round(float(pp),6),'oof_pred_t50':int(rr)})
        avg={k:round(statistics.mean([float(x[k]) for x in seed_metrics]),4) for k in ['pr_auc','roc_auc','f1','precision','recall','accuracy']}; std={k+'_std':round(statistics.stdev([float(x[k]) for x in seed_metrics]),4) for k in ['pr_auc','roc_auc','f1','precision','recall','accuracy']}
        flag,lr,top=feature_leak(rows,variant); summ.append({'variant':variant,'n_seeds':30,'eval_distribution':'full_imbalanced_validation_folds','positive_count':139,'negative_count':787,**avg,**std,'leakage_flag':flag}); leaks+=lr; tops+=top; held+=heldout(rows,variant)
    write_csv(DATA/'aggressive_filtered_full_eval_summary.csv',summ,['variant','n_seeds','eval_distribution','positive_count','negative_count','pr_auc','roc_auc','f1','precision','recall','accuracy','pr_auc_std','roc_auc_std','f1_std','precision_std','recall_std','accuracy_std','leakage_flag'])
    write_csv(DATA/'aggressive_filtered_full_eval_by_seed.csv',by,['variant','seed','n_rows','positive_count','negative_count','pr_auc','roc_auc','f1','precision','recall','accuracy'])
    write_csv(DATA/'aggressive_filtered_full_eval_thresholds.csv',th,['variant','seed','threshold','precision','recall','f1','meets_primary','meets_secondary'])
    write_csv(DATA/'aggressive_filtered_full_eval_source_metrics.csv',src,['variant','seed','source','n_rows','pr_auc','roc_auc','f1','precision','recall','accuracy'])
    write_csv(DATA/'aggressive_filtered_full_eval_source_heldout.csv',held,['variant','eval_scope','n_rows','pr_auc','roc_auc','f1','precision','recall','accuracy'])
    write_csv(DATA/'aggressive_filtered_full_eval_confusion_matrices.csv',cm,['variant','seed','actual_label','predicted_label','count'])
    write_csv(PRED/'aggressive_filtered_full_eval_oof_predictions.csv',predrows,['variant','seed','row_id','source','true_aggressive','oof_probability','oof_pred_t50'])
    write_csv(DIAG/'aggressive_filtered_full_eval_leakage.csv',leaks,['variant','class_label','token','feature','weight','rank_abs_weight','leakage_flag'])
    write_csv(DIAG/'aggressive_filtered_full_eval_top_features.csv',tops,['variant','rank','feature','weight'])
    write_csv(DIAG/'aggressive_filtered_full_eval_fold_diagnostics.csv',folddiag,['variant','seed','fold','train_full_rows','train_balanced_rows','train_positive_rows','train_negative_sampled_rows','validation_full_rows','validation_positive_rows','validation_negative_rows'])
    print('aggressive leakage-filtered done')
if __name__=='__main__': main()
