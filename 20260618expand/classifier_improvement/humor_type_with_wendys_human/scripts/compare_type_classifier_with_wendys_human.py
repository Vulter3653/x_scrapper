from __future__ import annotations
import csv,re,sys
from pathlib import Path
from collections import Counter
P=Path('/home/user/.local/pypackages')
if str(P) not in sys.path: sys.path.insert(0,str(P))
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.metrics import accuracy_score,confusion_matrix,f1_score,precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import FeatureUnion,Pipeline
ROOT=Path(__file__).resolve().parents[4]; BASE=ROOT/'20260618expand/classifier_improvement/humor_type_with_wendys_human'
DATA=BASE/'data'; DIAG=BASE/'diagnostics'; PRED=BASE/'predictions'
LABELS=['aggressive','affiliative','self-enhancing','self-defeating']; TOKENS=['wendy','wendys',"wendy's",'wendy’s','@wendys','frosty','baconator','nuggs','roast']
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def prep(t):
    t=re.sub(r'https?://\S+','<URL>',t or ''); t=re.sub(r'@\w+','<MENTION>',t); t=re.sub(r'#(\w+)',r'\1',t); return re.sub(r'\s+',' ',t.lower()).strip()
def pipe():
    return Pipeline([('vec',FeatureUnion([('word',TfidfVectorizer(analyzer='word',ngram_range=(1,2),max_features=5000,min_df=2,max_df=.95,sublinear_tf=True)),('char',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),max_features=5000,min_df=2,max_df=.95,sublinear_tf=True))])),('clf',OneVsRestClassifier(LogisticRegression(solver='liblinear',C=.1,class_weight='balanced',max_iter=2000,random_state=42)))])
def oof(rows,mid):
    X=[prep(r['text']) for r in rows]; y=np.array([LABELS.index(r['humor_type']) for r in rows]); pred=np.zeros(len(y),int)
    cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=42)
    for tr,te in cv.split(X,y):
        m=pipe(); m.fit([X[i] for i in tr],y[tr]); pred[te]=m.predict([X[i] for i in te])
    return y,pred
def main_metrics(mid,scope,y,pred):
    return {'model_id':mid,'eval_scope':scope,'eval_mode':'oof_stratified_5fold_cv','n_rows':len(y),'macro_f1':round(f1_score(y,pred,average='macro'),4),'weighted_f1':round(f1_score(y,pred,average='weighted'),4),'accuracy':round(accuracy_score(y,pred),4)}
def per_class(mid,scope,y,pred):
    p,r,f,s=precision_recall_fscore_support(y,pred,labels=list(range(4)),zero_division=0)
    return [{'model_id':mid,'eval_scope':scope,'class_label':LABELS[i],'support':int(s[i]),'precision':round(float(p[i]),4),'recall':round(float(r[i]),4),'f1':round(float(f[i]),4)} for i in range(4)]
def cm(mid,scope,y,pred):
    c=confusion_matrix(y,pred,labels=list(range(4))); return [{'model_id':mid,'eval_scope':scope,'actual_label':LABELS[i],'predicted_label':LABELS[j],'count':int(c[i,j])} for i in range(4) for j in range(4)]
def heldout(train,test,mid,scope):
    m=pipe(); m.fit([prep(r['text']) for r in train],[LABELS.index(r['humor_type']) for r in train]); y=np.array([LABELS.index(r['humor_type']) for r in test]); pred=m.predict([prep(r['text']) for r in test]); return main_metrics(mid,scope,y,pred),per_class(mid,scope,y,pred),cm(mid,scope,y,pred)
def source_metrics(rows,mid,y,pred):
    out=[]
    for src in sorted({r['source'] for r in rows}):
        idx=[i for i,r in enumerate(rows) if r['source']==src]
        out.append(main_metrics(mid,src,y[idx],pred[idx]))
    return out
def features(rows):
    m=pipe(); m.fit([prep(r['text']) for r in rows],[LABELS.index(r['humor_type']) for r in rows])
    names=[]
    for n,t in m.named_steps['vec'].transformer_list: names += [f'{n}__{x}' for x in t.get_feature_names_out()]
    co=np.vstack([est.coef_[0] for est in m.named_steps['clf'].estimators_]); outs=[]; leaks=[]; flag='PASS'
    for ci,lab in enumerate(LABELS):
        order=np.argsort(co[ci])[-25:][::-1]
        top=[names[i].lower() for i in order[:10]]
        for rank,i in enumerate(order,1): outs.append({'model_id':'type_model_b_batch1_plus_wendys_human','class_label':lab,'rank':rank,'feature':names[i],'weight':round(float(co[ci,i]),6)})
        for tok in TOKENS:
            ms=[(names[i],float(co[ci,i])) for i in range(len(names)) if tok in names[i].lower()]
            if any(tok in x for x in top): flag='FAIL'
            elif ms and flag!='FAIL': flag='WARN'
            for rank,(f,w) in enumerate(sorted(ms,key=lambda x:abs(x[1]),reverse=True)[:5],1): leaks.append({'model_id':'type_model_b_batch1_plus_wendys_human','class_label':lab,'diagnostic_token':tok,'feature':f,'weight':round(w,6),'rank_abs_weight':rank,'leakage_flag':'WARN'})
    if not leaks: leaks=[{'model_id':'type_model_b_batch1_plus_wendys_human','class_label':'all','diagnostic_token':'all','feature':'','weight':'','rank_abs_weight':'','leakage_flag':'PASS'}]
    for r in leaks: r['leakage_flag']=flag if r['leakage_flag']!='PASS' else r['leakage_flag']
    return outs,leaks,flag
def main():
    a=read(DATA/'type_training_batch1_only.csv'); b=read(DATA/'type_training_batch1_plus_wendys_human.csv'); w=[r for r in b if r['source']=='wendys_human_type']; b1=[r for r in b if r['source']=='batch1_fortune100']
    ya,pa=oof(a,'type_model_a_batch1_only'); yb,pb=oof(b,'type_model_b_batch1_plus_wendys_human')
    metrics=[main_metrics('type_model_a_batch1_only','all_training_rows',ya,pa),main_metrics('type_model_b_batch1_plus_wendys_human','all_training_rows',yb,pb)]
    pc=per_class('type_model_a_batch1_only','all_training_rows',ya,pa)+per_class('type_model_b_batch1_plus_wendys_human','all_training_rows',yb,pb)
    cms=cm('type_model_a_batch1_only','all_training_rows',ya,pa)+cm('type_model_b_batch1_plus_wendys_human','all_training_rows',yb,pb)
    sm=source_metrics(a,'type_model_a_batch1_only',ya,pa)+source_metrics(b,'type_model_b_batch1_plus_wendys_human',yb,pb)
    hm=[]; hpc=[]; hcm=[]
    for tr,te,mid,sc in [(b1,w,'type_model_a_batch1_only','train_batch1_test_wendys'),(w,b1,'type_model_b_wendys_only','train_wendys_test_batch1')]:
        m,pp,cc=heldout(tr,te,mid,sc); hm.append(m); hpc+=pp; hcm+=cc
    feat,leak,flag=features(b)
    arows=[]; brows=[]
    for r,pred in zip(a,pa): arows.append({'row_id':r['row_id'],'true_label':r['humor_type'],'pred_label':LABELS[int(pred)]})
    for r,pred in zip(b,pb): brows.append({'row_id':r['row_id'],'source':r['source'],'true_label':r['humor_type'],'pred_label':LABELS[int(pred)]})
    write(DATA/'type_model_comparison_metrics.csv',metrics,['model_id','eval_scope','eval_mode','n_rows','macro_f1','weighted_f1','accuracy'])
    write(DATA/'type_model_per_class_metrics.csv',pc+hpc,['model_id','eval_scope','class_label','support','precision','recall','f1'])
    write(DATA/'type_model_source_aware_metrics.csv',sm,['model_id','eval_scope','eval_mode','n_rows','macro_f1','weighted_f1','accuracy'])
    write(DATA/'type_model_source_heldout_metrics.csv',hm,['model_id','eval_scope','eval_mode','n_rows','macro_f1','weighted_f1','accuracy'])
    write(DATA/'type_model_confusion_matrices.csv',cms+hcm,['model_id','eval_scope','actual_label','predicted_label','count'])
    write(PRED/'type_model_a_oof_predictions.csv',arows,['row_id','true_label','pred_label']); write(PRED/'type_model_b_oof_predictions.csv',brows,['row_id','source','true_label','pred_label'])
    write(DIAG/'type_model_top_features.csv',feat,['model_id','class_label','rank','feature','weight']); write(DIAG/'type_model_leakage_diagnostic.csv',leak,['model_id','class_label','diagnostic_token','feature','weight','rank_abs_weight','leakage_flag'])
    print('Compared type classifiers'); print(metrics); print('leakage_flag='+flag)
if __name__=='__main__': main()
