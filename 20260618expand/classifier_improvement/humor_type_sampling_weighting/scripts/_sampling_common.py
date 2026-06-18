
from __future__ import annotations
import csv, re, sys, math, statistics
from pathlib import Path
from collections import Counter, defaultdict
P=Path('/home/user/.local/pypackages')
if str(P) not in sys.path: sys.path.insert(0,str(P))
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import FeatureUnion, Pipeline
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'20260618expand/classifier_improvement/humor_type_sampling_weighting'
DATA=BASE/'data'; DIAG=BASE/'diagnostics'; PRED=BASE/'predictions'
INPUT=ROOT/'20260618expand/classifier_improvement/humor_type_with_wendys_human/data/type_training_batch1_plus_wendys_human.csv'
LABELS=['aggressive','affiliative','self-enhancing','self-defeating']
TOKENS=['wendy','wendys',"wendy's",'wendy’s','@wendys','frosty','baconator','nuggs','roast']
SEEDS=list(range(30))
THRESH=[0.2,0.3,0.4,0.5,0.6,0.7,0.8]
def read_csv(p):
    with p.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows([{k:r.get(k,'') for k in fields} for r in rows])
def prep(t):
    t=re.sub(r'https?://\S+','<URL>',t or ''); t=re.sub(r'@\w+','<MENTION>',t); t=re.sub(r'#(\w+)',r'\1',t); return re.sub(r'\s+',' ',t.lower()).strip()
def make_vec():
    return FeatureUnion([('word',TfidfVectorizer(analyzer='word',ngram_range=(1,2),max_features=5000,min_df=2,max_df=.95,sublinear_tf=True)),('char',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),max_features=5000,min_df=2,max_df=.95,sublinear_tf=True))])
def make_binary(seed, class_weight=None):
    return Pipeline([('vec',make_vec()),('clf',LogisticRegression(solver='liblinear',C=.1,class_weight=class_weight,max_iter=2000,random_state=seed))])
def make_multi(seed, class_weight=None):
    return Pipeline([('vec',make_vec()),('clf',OneVsRestClassifier(LogisticRegression(solver='liblinear',C=.1,class_weight=class_weight,max_iter=2000,random_state=seed)))])
def label_idx(rows): return np.array([LABELS.index(r['humor_type']) for r in rows], dtype=int)
def ag_y(rows): return np.array([1 if r['humor_type']=='aggressive' else 0 for r in rows], dtype=int)
def split_oof_multi(rows, seed, class_weight=None, sample_weights=None):
    X=[prep(r['text']) for r in rows]; y=label_idx(rows); pred=np.zeros(len(y), dtype=int)
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    sw=np.array(sample_weights) if sample_weights is not None else None
    for tr,te in cv.split(X,y):
        if sw is None:
            m=make_multi(seed, class_weight); m.fit([X[i] for i in tr], y[tr]); pred[te]=m.predict([X[i] for i in te])
        else:
            vec=make_vec(); Xtr=vec.fit_transform([X[i] for i in tr]); Xte=vec.transform([X[i] for i in te]); scores=[]
            for cls in range(4):
                yy=(y[tr]==cls).astype(int)
                clf=LogisticRegression(solver='liblinear',C=.1,class_weight=class_weight,max_iter=2000,random_state=seed)
                clf.fit(Xtr, yy, sample_weight=sw[tr]); scores.append(clf.decision_function(Xte))
            pred[te]=np.vstack(scores).T.argmax(axis=1)
    return y,pred
def split_oof_bin(rows, seed, class_weight=None, sample_weights=None):
    X=[prep(r['text']) for r in rows]; y=ag_y(rows); prob=np.zeros(len(y)); pred=np.zeros(len(y), dtype=int)
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    sw=np.array(sample_weights) if sample_weights is not None else None
    for tr,te in cv.split(X,y):
        m=make_binary(seed, class_weight); fit_kw={}
        if sw is not None: fit_kw['clf__sample_weight']=sw[tr]
        m.fit([X[i] for i in tr], y[tr], **fit_kw); p=m.predict_proba([X[i] for i in te])[:,1]; prob[te]=p; pred[te]=(p>=.5).astype(int)
    return y,prob,pred
def multi_metric(y,pred): return {'macro_f1':round(f1_score(y,pred,average='macro'),4),'weighted_f1':round(f1_score(y,pred,average='weighted'),4),'accuracy':round(accuracy_score(y,pred),4)}
def per_class(y,pred):
    p,r,f,s=precision_recall_fscore_support(y,pred,labels=list(range(4)),zero_division=0)
    return [{'class_label':LABELS[i],'support':int(s[i]),'precision':round(float(p[i]),4),'recall':round(float(r[i]),4),'f1':round(float(f[i]),4)} for i in range(4)]
def bin_metric(y,prob,pred): return {'pr_auc':round(average_precision_score(y,prob),4),'roc_auc':round(roc_auc_score(y,prob),4),'f1':round(f1_score(y,pred,zero_division=0),4),'precision':round(precision_score(y,pred,zero_division=0),4),'recall':round(recall_score(y,pred,zero_division=0),4)}
def threshold_rows(prefix,y,prob):
    out=[]
    for t in THRESH:
        pred=(prob>=t).astype(int); prec=precision_score(y,pred,zero_division=0); rec=recall_score(y,pred,zero_division=0)
        out.append({**prefix,'threshold':t,'precision':round(prec,4),'recall':round(rec,4),'f1':round(f1_score(y,pred,zero_division=0),4),'meets_primary':'yes' if prec>=.60 and rec>=.20 else 'no','meets_secondary':'yes' if prec>=.50 and rec>=.30 else 'no'})
    return out
def leakage_multi(rows, seed, class_weight=None, sample_weights=None):
    X=[prep(r['text']) for r in rows]; y=label_idx(rows); sw=np.array(sample_weights) if sample_weights is not None else None
    if sw is None:
        m=make_multi(seed,class_weight); m.fit(X,y); names=[]
        for n,t in m.named_steps['vec'].transformer_list: names += [f'{n}__{x}' for x in t.get_feature_names_out()]
        co=np.vstack([est.coef_[0] for est in m.named_steps['clf'].estimators_]); return leak_from_weights(names,co)
    vec=make_vec(); Xt=vec.fit_transform(X); names=[]
    for n,t in vec.transformer_list: names += [f'{n}__{x}' for x in t.get_feature_names_out()]
    co=[]
    for cls in range(4):
        yy=(y==cls).astype(int); clf=LogisticRegression(solver='liblinear',C=.1,class_weight=class_weight,max_iter=2000,random_state=seed)
        clf.fit(Xt, yy, sample_weight=sw); co.append(clf.coef_[0])
    return leak_from_weights(names,np.vstack(co))
def leakage_bin(rows, seed, class_weight=None, sample_weights=None):
    X=[prep(r['text']) for r in rows]; y=ag_y(rows); m=make_binary(seed,class_weight); fit_kw={}
    if sample_weights is not None: fit_kw['clf__sample_weight']=np.array(sample_weights)
    m.fit(X,y,**fit_kw); names=[]
    for n,t in m.named_steps['vec'].transformer_list: names += [f'{n}__{x}' for x in t.get_feature_names_out()]
    return leak_from_weights(names, m.named_steps['clf'].coef_)
def leak_from_weights(names, co):
    flag='PASS'; rows=[]; mat=np.atleast_2d(co)
    for ci,vec in enumerate(mat):
        top={names[i].lower() for i in np.argsort(vec)[-10:][::-1]}
        cls=LABELS[ci] if len(mat)==4 else 'aggressive'
        for tok in TOKENS:
            ms=[(names[i],float(vec[i])) for i in range(len(names)) if tok in names[i].lower()]
            if any(tok in x for x in top): flag='FAIL'
            elif ms and flag!='FAIL': flag='WARN'
            for rank,(f,w) in enumerate(sorted(ms,key=lambda x:abs(x[1]),reverse=True)[:5],1): rows.append({'class_label':cls,'diagnostic_token':tok,'feature':f,'weight':round(w,6),'rank_abs_weight':rank})
    if not rows: rows=[{'class_label':'all','diagnostic_token':'all','feature':'','weight':'','rank_abs_weight':''}]
    for r in rows: r['leakage_flag']=flag
    return flag,rows
