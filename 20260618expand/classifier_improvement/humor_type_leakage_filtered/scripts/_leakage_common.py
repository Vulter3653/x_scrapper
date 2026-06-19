from __future__ import annotations
import csv,re,sys,statistics,random
from pathlib import Path
from collections import Counter,defaultdict
P=Path('/home/user/.local/pypackages')
if str(P) not in sys.path: sys.path.insert(0,str(P))
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score,average_precision_score,confusion_matrix,f1_score,precision_score,recall_score,roc_auc_score,precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import FeatureUnion,Pipeline
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'20260618expand/classifier_improvement/humor_type_leakage_filtered'
DATA=BASE/'data'; DIAG=BASE/'diagnostics'; PRED=BASE/'predictions'
INPUT=ROOT/'20260618expand/classifier_improvement/humor_type_with_wendys_human/data/type_training_batch1_plus_wendys_human.csv'
LABELS=['aggressive','affiliative','self-enhancing','self-defeating']; SEEDS=list(range(30)); THRESH=[0.2,0.3,0.4,0.5,0.6,0.7,0.8]
TOKEN_GROUPS={
 'wendys_brand':['wendy','wendys','wendy’s',"wendy's",'@wendys'],
 'brand_product':['wendy','wendys','wendy’s',"wendy's",'@wendys','frosty','nuggs','nuggets','spicy nuggets','jr frosty','frostyccino'],
 'competitor_roast':['bk','clown','roast','roasting','diss','disrespectful','savage'],
 'campaign_product':['free','app','drive-thru','drive thru','breakfast','fries','chicken sandwich','nuggets','coupon','deal','offer']}
VARIANTS=[('original_text',[]),('mask_wendys_brand',['wendys_brand']),('mask_brand_product',['brand_product']),('mask_brand_product_competitor',['brand_product','competitor_roast']),('mask_campaign_product',['campaign_product']),('mask_all_leakage_groups',['brand_product','competitor_roast','campaign_product'])]
PLACE={'wendys_brand':'<BRAND_TOKEN>','brand_product':'<PRODUCT_TOKEN>','competitor_roast':'<COMPETITOR_TOKEN>','campaign_product':'<CAMPAIGN_TOKEN>'}
def read_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write_csv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows([{k:r.get(k,'') for k in fields} for r in rows])
def text_has(text,token): return re.search(r'(?i)(?<!\w)'+re.escape(token)+r'(?!\w)',text or '') is not None
def mask_text(text,groups):
    out=text or ''; n=0
    for g in groups:
        for tok in sorted(TOKEN_GROUPS[g],key=len,reverse=True):
            pat=re.compile(r'(?i)(?<!\w)'+re.escape(tok)+r'(?!\w)')
            out,c=pat.subn(PLACE[g],out); n+=c
    return re.sub(r'\s+',' ',out).strip(),n
def prep(t):
    t=re.sub(r'https?://\S+','<URL>',t or ''); t=re.sub(r'@\w+','<MENTION>',t); t=re.sub(r'#(\w+)',r'\1',t); return re.sub(r'\s+',' ',t.lower()).strip()
def make_vec(): return FeatureUnion([('word',TfidfVectorizer(analyzer='word',ngram_range=(1,2),max_features=5000,min_df=2,max_df=.95,sublinear_tf=True)),('char',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),max_features=5000,min_df=2,max_df=.95,sublinear_tf=True))])
def make_bin(seed): return Pipeline([('vec',make_vec()),('clf',LogisticRegression(solver='liblinear',C=.1,class_weight=None,max_iter=2000,random_state=seed))])
def make_multi(seed): return Pipeline([('vec',make_vec()),('clf',OneVsRestClassifier(LogisticRegression(solver='liblinear',C=.1,class_weight='balanced',max_iter=2000,random_state=seed)))])
def y_type(rows): return np.array([LABELS.index(r['humor_type']) for r in rows])
def y_ag(rows): return np.array([1 if r['humor_type']=='aggressive' else 0 for r in rows])
def bin_metric(y,p,pr): return {'pr_auc':round(average_precision_score(y,p),4),'roc_auc':round(roc_auc_score(y,p),4),'f1':round(f1_score(y,pr,zero_division=0),4),'precision':round(precision_score(y,pr,zero_division=0),4),'recall':round(recall_score(y,pr,zero_division=0),4),'accuracy':round(accuracy_score(y,pr),4)}
def multi_metric(y,pr): return {'macro_f1':round(f1_score(y,pr,average='macro'),4),'weighted_f1':round(f1_score(y,pr,average='weighted'),4),'accuracy':round(accuracy_score(y,pr),4)}
def per_class(y,pr):
    p,r,f,s=precision_recall_fscore_support(y,pr,labels=list(range(4)),zero_division=0)
    return [{'class_label':LABELS[i],'support':int(s[i]),'precision':round(float(p[i]),4),'recall':round(float(r[i]),4),'f1':round(float(f[i]),4)} for i in range(4)]
def thresholds(prefix,y,p):
    out=[]
    for t in THRESH:
        pr=(p>=t).astype(int); prec=precision_score(y,pr,zero_division=0); rec=recall_score(y,pr,zero_division=0)
        out.append({**prefix,'threshold':t,'precision':round(prec,4),'recall':round(rec,4),'f1':round(f1_score(y,pr,zero_division=0),4),'meets_primary':'yes' if prec>=.60 and rec>=.20 else 'no','meets_secondary':'yes' if prec>=.50 and rec>=.30 else 'no'})
    return out
def leakage_from_model(m,binary=False):
    names=[]
    for n,t in m.named_steps['vec'].transformer_list: names += [f'{n}__{x}' for x in t.get_feature_names_out()]
    co=m.named_steps['clf'].coef_ if binary else np.vstack([e.coef_[0] for e in m.named_steps['clf'].estimators_])
    flag='PASS'; rows=[]; mat=np.atleast_2d(co)
    toks=sum(TOKEN_GROUPS.values(),[])
    for ci,vec in enumerate(mat):
        cls='aggressive' if binary else LABELS[ci]; top={names[i].lower() for i in np.argsort(vec)[-20:][::-1]}
        for tok in toks:
            ms=[(names[i],float(vec[i])) for i in range(len(names)) if tok.lower() in names[i].lower()]
            if any(tok.lower() in x for x in top): flag='FAIL'
            elif ms and flag!='FAIL': flag='WARN'
            for rank,(f,w) in enumerate(sorted(ms,key=lambda x:abs(x[1]),reverse=True)[:3],1): rows.append({'class_label':cls,'token':tok,'feature':f,'weight':round(w,6),'rank_abs_weight':rank})
    if not rows: rows=[{'class_label':'all','token':'all','feature':'','weight':'','rank_abs_weight':''}]
    for r in rows: r['leakage_flag']=flag
    return flag,rows
