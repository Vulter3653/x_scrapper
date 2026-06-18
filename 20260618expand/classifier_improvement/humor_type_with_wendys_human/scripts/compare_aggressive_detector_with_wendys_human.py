from __future__ import annotations
import csv,re,sys
from pathlib import Path
P=Path('/home/user/.local/pypackages')
if str(P) not in sys.path: sys.path.insert(0,str(P))
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score,roc_auc_score,f1_score,precision_score,recall_score,confusion_matrix
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import FeatureUnion,Pipeline
ROOT=Path(__file__).resolve().parents[4]; BASE=ROOT/'20260618expand/classifier_improvement/humor_type_with_wendys_human'; DATA=BASE/'data'; DIAG=BASE/'diagnostics'; PRED=BASE/'predictions'
TOKENS=['wendy','wendys',"wendy's",'wendy’s','@wendys','frosty','baconator','nuggs','roast','competitor']
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def prep(t):
    t=re.sub(r'https?://\S+','<URL>',t or ''); t=re.sub(r'@\w+','<MENTION>',t); t=re.sub(r'#(\w+)',r'\1',t); return re.sub(r'\s+',' ',t.lower()).strip()
def pipe():
    return Pipeline([('vec',FeatureUnion([('word',TfidfVectorizer(analyzer='word',ngram_range=(1,2),max_features=5000,min_df=2,max_df=.95,sublinear_tf=True)),('char',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),max_features=5000,min_df=2,max_df=.95,sublinear_tf=True))])),('clf',LogisticRegression(solver='liblinear',C=.1,class_weight='balanced',max_iter=2000,random_state=42))])
def labels(rows): return np.array([1 if r['humor_type']=='aggressive' else 0 for r in rows])
def oof(rows):
    X=[prep(r['text']) for r in rows]; y=labels(rows); p=np.zeros(len(y)); pred=np.zeros(len(y),int); cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=42)
    for tr,te in cv.split(X,y):
        m=pipe(); m.fit([X[i] for i in tr],y[tr]); pp=m.predict_proba([X[i] for i in te])[:,1]; p[te]=pp; pred[te]=(pp>=.5).astype(int)
    return y,p,pred
def met(mid,scope,mode,y,p,pred):
    return {'model_id':mid,'eval_scope':scope,'eval_mode':mode,'n_rows':len(y),'aggressive_count':int(y.sum()),'other_count':int(len(y)-y.sum()),'pr_auc':round(average_precision_score(y,p),4),'roc_auc':round(roc_auc_score(y,p),4),'f1':round(f1_score(y,pred,zero_division=0),4),'precision':round(precision_score(y,pred,zero_division=0),4),'recall':round(recall_score(y,pred,zero_division=0),4)}
def cm(mid,scope,y,pred):
    c=confusion_matrix(y,pred,labels=[0,1]); names=['other_humor','aggressive']; return [{'model_id':mid,'eval_scope':scope,'actual_label':names[i],'predicted_label':names[j],'count':int(c[i,j])} for i in range(2) for j in range(2)]
def thresh(mid,y,p):
    out=[]
    for t in [.2,.3,.4,.5,.6,.7,.8]:
        pr=(p>=t).astype(int); prec=precision_score(y,pr,zero_division=0); rec=recall_score(y,pr,zero_division=0)
        out.append({'model_id':mid,'threshold':t,'precision':round(prec,4),'recall':round(rec,4),'f1':round(f1_score(y,pr,zero_division=0),4),'meets_primary': 'yes' if prec>=.60 and rec>=.20 else 'no','meets_secondary':'yes' if prec>=.50 and rec>=.30 else 'no'})
    return out
def held(train,test,mid,scope):
    m=pipe(); m.fit([prep(r['text']) for r in train],labels(train)); y=labels(test); p=m.predict_proba([prep(r['text']) for r in test])[:,1]; pred=(p>=.5).astype(int); return met(mid,scope,'source_heldout',y,p,pred),cm(mid,scope,y,pred)
def source(rows,mid,y,p,pred):
    out=[]
    for src in sorted({r['source'] for r in rows}):
        idx=[i for i,r in enumerate(rows) if r['source']==src]
        out.append(met(mid,src,'oof_source_subset',y[idx],p[idx],pred[idx]))
    return out
def feats(rows):
    m=pipe(); y=labels(rows); m.fit([prep(r['text']) for r in rows],y)
    names=[]
    for n,t in m.named_steps['vec'].transformer_list: names += [f'{n}__{x}' for x in t.get_feature_names_out()]
    co=m.named_steps['clf'].coef_[0]; order=np.argsort(co)[-50:][::-1]
    f=[{'model_id':'aggressive_detector_b','rank':i+1,'feature':names[idx],'weight':round(float(co[idx]),6)} for i,idx in enumerate(order)]
    top={names[i].lower() for i in order[:10]}; flag='PASS'; leaks=[]
    for tok in TOKENS:
        ms=[(names[i],float(co[i])) for i in range(len(names)) if tok in names[i].lower()]
        if any(tok in x for x in top): flag='FAIL'
        elif ms and flag!='FAIL': flag='WARN'
        for rank,(ff,w) in enumerate(sorted(ms,key=lambda x:abs(x[1]),reverse=True)[:10],1): leaks.append({'diagnostic_token':tok,'feature':ff,'weight':round(w,6),'rank_abs_weight':rank,'leakage_flag':'WARN'})
    if not leaks: leaks=[{'diagnostic_token':'all','feature':'','weight':'','rank_abs_weight':'','leakage_flag':'PASS'}]
    for r in leaks:
        if r['leakage_flag']!='PASS': r['leakage_flag']=flag
    return f,leaks,flag

def fval(x):
    try: return float(x)
    except Exception: return 0.0
def read_rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write_summary(ag_metrics, thresholds, ag_leak_flag):
    type_metrics=read_rows(DATA/'type_model_comparison_metrics.csv')
    per=read_rows(DATA/'type_model_per_class_metrics.csv')
    held=read_rows(DATA/'type_model_source_heldout_metrics.csv')
    type_leaks=read_rows(DIAG/'type_model_leakage_diagnostic.csv')
    type_flag='FAIL' if any(r.get('leakage_flag')=='FAIL' for r in type_leaks) else ('WARN' if any(r.get('leakage_flag')=='WARN' for r in type_leaks) else 'PASS')
    ta=next(r for r in type_metrics if r['model_id']=='type_model_a_batch1_only')
    tb=next(r for r in type_metrics if r['model_id']=='type_model_b_batch1_plus_wendys_human')
    def pc(mid,lab): return next(r for r in per if r['model_id']==mid and r['eval_scope']=='all_training_rows' and r['class_label']==lab)
    a_ag,b_ag=pc('type_model_a_batch1_only','aggressive'),pc('type_model_b_batch1_plus_wendys_human','aggressive')
    a_sd,b_sd=pc('type_model_a_batch1_only','self-defeating'),pc('type_model_b_batch1_plus_wendys_human','self-defeating')
    type_candidate=(fval(tb['macro_f1'])>fval(ta['macro_f1']) and fval(b_ag['f1'])>fval(a_ag['f1']) and fval(b_ag['recall'])>fval(a_ag['recall']) and fval(b_sd['f1'])>=max(0.0,fval(a_sd['f1'])-0.10) and type_flag!='FAIL')
    type_status='type_model_b_candidate_only' if type_candidate else 'retain_type_model_a_candidate'
    aa=next(r for r in ag_metrics if r['model_id']=='aggressive_detector_a_batch1_only')
    ab=next(r for r in ag_metrics if r['model_id']=='aggressive_detector_b_batch1_plus_wendys_human')
    primary=any(r['model_id']=='aggressive_detector_b_batch1_plus_wendys_human' and r['meets_primary']=='yes' for r in thresholds)
    secondary=any(r['model_id']=='aggressive_detector_b_batch1_plus_wendys_human' and r['meets_secondary']=='yes' for r in thresholds)
    ag_candidate=(fval(ab['pr_auc'])>fval(aa['pr_auc']) and (primary or secondary) and ag_leak_flag!='FAIL')
    ag_status='aggressive_detector_b_candidate_only' if ag_candidate else 'retain_aggressive_detector_a_candidate'
    write(DATA/'type_and_aggressive_model_summary.csv',[
        {'model_family':'4class_type','candidate_status':type_status,'leakage_flag':type_flag,'model_a_primary_metric':ta['macro_f1'],'model_b_primary_metric':tb['macro_f1'],'notes':'candidate only; not deployed'},
        {'model_family':'aggressive_detector','candidate_status':ag_status,'leakage_flag':ag_leak_flag,'model_a_primary_metric':aa['pr_auc'],'model_b_primary_metric':ab['pr_auc'],'notes':'candidate only; not deployed'},
    ],['model_family','candidate_status','leakage_flag','model_a_primary_metric','model_b_primary_metric','notes'])
    write(DIAG/'validation_summary.csv',[
        {'check':'type_model_candidate_status','status':type_status},
        {'check':'aggressive_detector_candidate_status','status':ag_status},
        {'check':'model_prediction_564_rows_used','status':'NO'},
        {'check':'integrated_corpus_reclassification','status':'NOT_RUN'},
        {'check':'h1_h2_h3_regression','status':'NOT_RUN'},
        {'check':'data_collection_workflow','status':'NOT_MODIFIED'},
    ],['check','status'])

def main():
    a=read(DATA/'type_training_batch1_only.csv'); b=read(DATA/'type_training_batch1_plus_wendys_human.csv'); b1=[r for r in b if r['source']=='batch1_fortune100']; w=[r for r in b if r['source']=='wendys_human_type']
    ya,pa,pra=oof(a); yb,pb,prb=oof(b)
    mets=[met('aggressive_detector_a_batch1_only','all_training_rows','oof_stratified_5fold_cv',ya,pa,pra),met('aggressive_detector_b_batch1_plus_wendys_human','all_training_rows','oof_stratified_5fold_cv',yb,pb,prb)]
    th=thresh('aggressive_detector_a_batch1_only',ya,pa)+thresh('aggressive_detector_b_batch1_plus_wendys_human',yb,pb)
    so=source(a,'aggressive_detector_a_batch1_only',ya,pa,pra)+source(b,'aggressive_detector_b_batch1_plus_wendys_human',yb,pb,prb)
    h1,c1=held(b1,w,'aggressive_detector_a_batch1_only','train_batch1_test_wendys'); h2,c2=held(w,b1,'aggressive_detector_b_wendys_only','train_wendys_test_batch1')
    feat,leak,flag=feats(b); preds=[{'row_id':r['row_id'],'source':r['source'],'true_aggressive':int(y),'oof_probability':round(float(p),6),'oof_pred_t50':int(pr)} for r,y,p,pr in zip(b,yb,pb,prb)]
    write(DATA/'aggressive_detector_metrics.csv',mets,['model_id','eval_scope','eval_mode','n_rows','aggressive_count','other_count','pr_auc','roc_auc','f1','precision','recall'])
    write(DATA/'aggressive_detector_threshold_diagnostics.csv',th,['model_id','threshold','precision','recall','f1','meets_primary','meets_secondary'])
    write(DATA/'aggressive_detector_source_aware_metrics.csv',so,['model_id','eval_scope','eval_mode','n_rows','aggressive_count','other_count','pr_auc','roc_auc','f1','precision','recall'])
    write(DATA/'aggressive_detector_source_heldout_metrics.csv',[h1,h2],['model_id','eval_scope','eval_mode','n_rows','aggressive_count','other_count','pr_auc','roc_auc','f1','precision','recall'])
    write(DATA/'aggressive_detector_confusion_matrices.csv',cm('aggressive_detector_a_batch1_only','all_training_rows',ya,pra)+cm('aggressive_detector_b_batch1_plus_wendys_human','all_training_rows',yb,prb)+c1+c2,['model_id','eval_scope','actual_label','predicted_label','count'])
    write(PRED/'aggressive_detector_oof_predictions.csv',preds,['row_id','source','true_aggressive','oof_probability','oof_pred_t50'])
    write(DIAG/'aggressive_detector_top_features.csv',feat,['model_id','rank','feature','weight']); write(DIAG/'aggressive_detector_leakage_diagnostic.csv',leak,['diagnostic_token','feature','weight','rank_abs_weight','leakage_flag'])
    write_summary(mets, th, flag)
    print('Compared aggressive detectors'); print(mets); print('leakage_flag='+flag)
if __name__=='__main__': main()
