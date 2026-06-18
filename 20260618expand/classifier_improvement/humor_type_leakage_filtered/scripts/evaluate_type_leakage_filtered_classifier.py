from _leakage_common import *
TEXTCOL={'original_text':'text_original','mask_wendys_brand':'text_mask_wendys_brand','mask_brand_product':'text_mask_brand_product','mask_brand_product_competitor':'text_mask_brand_product_competitor','mask_campaign_product':'text_mask_campaign_product','mask_all_leakage_groups':'text_mask_all_leakage_groups'}
def eval_oof(rows,variant):
    col=TEXTCOL[variant]; X=[prep(r[col]) for r in rows]; y=y_type(rows); pr=np.zeros(len(y),int); cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=42)
    for tr,te in cv.split(X,y):
        m=make_multi(42); m.fit([X[i] for i in tr],y[tr]); pr[te]=m.predict([X[i] for i in te])
    return y,pr
def source(rows,variant,y,pr):
    out=[]
    for src in sorted({r['source'] for r in rows}):
        idx=[i for i,r in enumerate(rows) if r['source']==src]
        out.append({'variant':variant,'source':src,'n_rows':len(idx),**multi_metric(y[idx],pr[idx])})
    return out
def heldout(rows,variant):
    col=TEXTCOL[variant]; b=[r for r in rows if r['source']=='batch1_fortune100']; w=[r for r in rows if r['source']=='wendys_human_type']; out=[]
    for scope,tr,te in [('train_batch1_test_wendys',b,w),('train_wendys_test_batch1',w,b)]:
        m=make_multi(42); m.fit([prep(r[col]) for r in tr],y_type(tr)); y=y_type(te); pr=m.predict([prep(r[col]) for r in te]); out.append({'variant':variant,'eval_scope':scope,'n_rows':len(te),**multi_metric(y,pr)})
    return out
def feature_leak(rows,variant):
    col=TEXTCOL[variant]; m=make_multi(42); m.fit([prep(r[col]) for r in rows],y_type(rows)); flag,lr=leakage_from_model(m,False); names=[]
    for n,t in m.named_steps['vec'].transformer_list: names += [f'{n}__{x}' for x in t.get_feature_names_out()]
    co=np.vstack([e.coef_[0] for e in m.named_steps['clf'].estimators_]); top=[]
    for ci,lab in enumerate(LABELS):
        for rank,idx in enumerate(np.argsort(co[ci])[-25:][::-1],1): top.append({'variant':variant,'class_label':lab,'rank':rank,'feature':names[idx],'weight':round(float(co[ci,idx]),6)})
    for r in lr: r['variant']=variant
    return flag,lr,top
def cm_rows(variant,y,pr):
    c=confusion_matrix(y,pr,labels=list(range(4))); return [{'variant':variant,'actual_label':LABELS[i],'predicted_label':LABELS[j],'count':int(c[i,j])} for i in range(4) for j in range(4)]
def main():
    rows=read_csv(DATA/'type_training_leakage_filtered_variants.csv'); metrics=[]; pc=[]; src=[]; held=[]; cms=[]; preds=[]; leaks=[]; tops=[]
    for variant in TEXTCOL:
        y,pr=eval_oof(rows,variant); m=multi_metric(y,pr); per=per_class(y,pr); flag,lr,top=feature_leak(rows,variant)
        metrics.append({'variant':variant,'n_rows':len(rows),**m,'aggressive_f1':next(x['f1'] for x in per if x['class_label']=='aggressive'),'self_defeating_f1':next(x['f1'] for x in per if x['class_label']=='self-defeating'),'leakage_flag':flag})
        for r in per: pc.append({'variant':variant,**r})
        src+=source(rows,variant,y,pr); held+=heldout(rows,variant); cms+=cm_rows(variant,y,pr); leaks+=lr; tops+=top
        for r,yy,pp in zip(rows,y,pr): preds.append({'variant':variant,'row_id':r['row_id'],'source':r['source'],'true_label':LABELS[int(yy)],'pred_label':LABELS[int(pp)]})
    write_csv(DATA/'type_filtered_metrics.csv',metrics,['variant','n_rows','macro_f1','weighted_f1','accuracy','aggressive_f1','self_defeating_f1','leakage_flag'])
    write_csv(DATA/'type_filtered_per_class_metrics.csv',pc,['variant','class_label','support','precision','recall','f1'])
    write_csv(DATA/'type_filtered_source_metrics.csv',src,['variant','source','n_rows','macro_f1','weighted_f1','accuracy'])
    write_csv(DATA/'type_filtered_source_heldout.csv',held,['variant','eval_scope','n_rows','macro_f1','weighted_f1','accuracy'])
    write_csv(DATA/'type_filtered_confusion_matrices.csv',cms,['variant','actual_label','predicted_label','count'])
    write_csv(PRED/'type_filtered_oof_predictions.csv',preds,['variant','row_id','source','true_label','pred_label'])
    write_csv(DIAG/'type_filtered_leakage.csv',leaks,['variant','class_label','token','feature','weight','rank_abs_weight','leakage_flag'])
    write_csv(DIAG/'type_filtered_top_features.csv',tops,['variant','class_label','rank','feature','weight'])
    print('type leakage-filtered done')
if __name__=='__main__': main()
