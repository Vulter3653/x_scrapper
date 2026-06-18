from __future__ import annotations
import csv, re, hashlib
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'20260618expand/classifier_improvement/humor_type_with_wendys_human'
DATA=BASE/'data'; DIAG=BASE/'diagnostics'
SPLITS=ROOT/'20260618expand/classifier_improvement/data/human_labeling_template/coder_splits'
WFILES=[ROOT/"20260615wendy's/data/wendys_h2_four_type_humor_dataset.csv",ROOT/"20260615wendy's/data/wendys_full_sample_four_type_humor_classifier_dataset.csv",ROOT/"20260615wendy's/data/wendys_h2_coder1_priority_dataset.csv"]
TYPE_MAP={'1':'aggressive','2':'affiliative','3':'self-enhancing','4':'self-defeating','aggressive':'aggressive','affiliative':'affiliative','self-enhancing':'self-enhancing','self_enhancing':'self-enhancing','self defeating':'self-defeating','self-defeating':'self-defeating','self_defeating':'self-defeating'}
OUT_FIELDS=['row_id','source','original_file','company_name','tweet_id','tweet_url','created_at','text','humor_presence_binary','humor_type','original_type_value','label_source_detail']
def read_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write_csv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    clean=[{k:r.get(k,'') for k in fields} for r in rows]
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(clean)
def norm(s): return re.sub(r'\s+',' ',(s or '').strip())
def h(s): return hashlib.sha1(norm(s).lower().encode()).hexdigest()[:16]
def sid(url):
    m=re.search(r'/status/(\d+)',url or ''); return m.group(1) if m else ''
def key(r):
    if r.get('tweet_id'): return 'tweet_id:'+r['tweet_id']
    if sid(r.get('tweet_url','')): return 'tweet_id:'+sid(r.get('tweet_url',''))
    return 'text:'+h(r.get('text',''))+':'+(r.get('created_at','') or '')
def map_type(v): return TYPE_MAP.get((v or '').strip().lower())
def batch1():
    rows=[]; excl=[]
    for coder in ['coder1','coder2','coder3']:
        p=SPLITS/f'{coder}_labeling_template.csv'
        for i,r in enumerate(read_csv(p),2):
            pres=(r.get('유머_존재여부') or '').strip(); tv=(r.get('유머_유형') or '').strip(); t=map_type(tv)
            if pres=='1' and t:
                rows.append({'row_id':'','source':'batch1_fortune100','original_file':str(p.relative_to(ROOT)),'company_name':r.get('회사명',''),'tweet_id':r.get('트윗_ID',''),'tweet_url':r.get('트윗_URL',''),'created_at':r.get('작성일시',''),'text':norm(r.get('본문','')),'humor_presence_binary':'1','humor_type':t,'original_type_value':tv,'label_source_detail':coder})
            else:
                excl.append({'source':'batch1_fortune100','original_file':str(p.relative_to(ROOT)),'reason':'not_humor_or_missing_type','row_number':i})
    return rows,excl
def wendy_candidates():
    inv=[]; raw=[]; excl=[]
    for p in WFILES:
        rows=read_csv(p); fields=list(rows[0].keys()) if rows else []
        label_cols=[c for c in ['final_humor_type','label'] if c in fields]
        inv.append({'source_file':str(p.relative_to(ROOT)),'raw_rows':len(rows),'label_columns':';'.join(label_cols),'usable_for_training':'yes','note':'human-coded type source candidate; deduped before final use'})
        for i,r in enumerate(rows,2):
            tv=r.get('final_humor_type') or r.get('label') or ''
            t=map_type(tv)
            pres=r.get('final_humor_binary','1')
            available=r.get('final_humor_type_available','1')
            tid=r.get('id','') or r.get('tweet_id','')
            url=r.get('tweet_url','') or (f'https://x.com/Wendys/status/{tid}' if tid else '')
            text=norm(r.get('text',''))
            if pres in {'0','false','False'} or available in {'0','false','False'} or not t or not text:
                excl.append({'source':'wendys_human_type','original_file':str(p.relative_to(ROOT)),'reason':'non_humor_missing_or_non_type','row_number':i})
                continue
            raw.append({'row_id':'','source':'wendys_human_type','original_file':str(p.relative_to(ROOT)),'company_name':"Wendy's",'tweet_id':tid,'tweet_url':url,'created_at':'','text':text,'humor_presence_binary':'1','humor_type':t,'original_type_value':tv,'label_source_detail':r.get('final_humor_type_source','') or str(p.name),'dedupe_key':''})
    inv.append({'source_file':'slide/model_prediction_type_distribution','raw_rows':564,'label_columns':'model_predicted_type','usable_for_training':'no','note':'model prediction only rows excluded from supervised training'})
    return inv,raw,excl
def dedupe(rows):
    groups=defaultdict(list); conflicts=[]; dups=[]; final=[]
    for r in rows:
        r['dedupe_key']=key(r); groups[r['dedupe_key']].append(r)
    pref=["20260615wendy's/data/wendys_h2_four_type_humor_dataset.csv","20260615wendy's/data/wendys_full_sample_four_type_humor_classifier_dataset.csv","20260615wendy's/data/wendys_h2_coder1_priority_dataset.csv"]
    for k,g in groups.items():
        labs=sorted({x['humor_type'] for x in g})
        if len(labs)>1:
            for x in g: conflicts.append({**x,'conflict_key':k,'conflicting_labels':';'.join(labs)})
            continue
        g=sorted(g,key=lambda x: pref.index(x['original_file']) if x['original_file'] in pref else 99)
        final.append(g[0])
        for x in g[1:]: dups.append({**x,'duplicate_key':k,'duplicate_of':g[0]['original_file']})
    return final,dups,conflicts
def main():
    DATA.mkdir(parents=True,exist_ok=True); DIAG.mkdir(parents=True,exist_ok=True)
    b,be=batch1(); inv,wraw,we=wendy_candidates(); w,dups,conf=dedupe(wraw)
    for i,r in enumerate(b,1): r['row_id']=f'type_b1_{i:04d}'
    for i,r in enumerate(w,1): r['row_id']=f'type_wendy_{i:04d}'
    comb=b+w
    for i,r in enumerate(comb,1): r['row_id']=f'type_combined_{i:04d}'
    write_csv(DATA/'type_training_batch1_only.csv',b,OUT_FIELDS)
    write_csv(DATA/'type_training_batch1_plus_wendys_human.csv',comb,OUT_FIELDS)
    dist=[]
    for name,rr in [('batch1_fortune100',b),('wendys_human_type',w),('combined',comb)]:
        c=Counter(x['humor_type'] for x in rr)
        for lab in ['aggressive','affiliative','self-enhancing','self-defeating']:
            dist.append({'dataset':name,'humor_type':lab,'count':c.get(lab,0)})
        dist.append({'dataset':name,'humor_type':'TOTAL','count':len(rr)})
    write_csv(DIAG/'type_training_label_distribution.csv',dist,['dataset','humor_type','count'])
    write_csv(DIAG/'type_training_source_inventory.csv',inv,['source_file','raw_rows','label_columns','usable_for_training','note'])
    write_csv(DIAG/'type_training_duplicate_diagnostics.csv',dups, list(dups[0].keys()) if dups else OUT_FIELDS+['dedupe_key','duplicate_key','duplicate_of'])
    write_csv(DIAG/'type_training_conflict_diagnostics.csv',conf, list(conf[0].keys()) if conf else OUT_FIELDS+['dedupe_key','conflict_key','conflicting_labels'])
    excl=[*be,*we,{'source':'wendys_model_prediction','original_file':'slide/model_prediction_type_distribution','reason':'model_prediction_only_not_training_label','row_number':564}]
    write_csv(DIAG/'type_training_exclusion_summary.csv',excl,['source','original_file','reason','row_number'])
    print('Built type training data'); print(f'batch1_rows={len(b)}'); print(f'wendys_rows={len(w)}'); print(f'combined_rows={len(comb)}')
if __name__=='__main__': main()
