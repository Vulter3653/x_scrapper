from _leakage_common import *
def main():
    rows=read_csv(INPUT); out=[]
    for group,toks in TOKEN_GROUPS.items():
        for tok in toks:
            present=[r for r in rows if text_has(r['text'],tok)]; b=[r for r in present if r['source']=='batch1_fortune100']; w=[r for r in present if r['source']=='wendys_human_type']; ag=[r for r in present if r['humor_type']=='aggressive']; non=len(present)-len(ag)
            skew=round((len(w)+1)/(len(b)+1),4)
            out.append({'token':tok,'token_group':group,'total_count':len(present),'batch1_count':len(b),'wendys_count':len(w),'aggressive_count':len(ag),'non_aggressive_count':non,'aggressive_rate_when_present':round(len(ag)/len(present),4) if present else 0,'source_skew_ratio':skew,'include_in_mask_group':'yes'})
    write_csv(DIAG/'leakage_token_inventory.csv',out,['token','token_group','total_count','batch1_count','wendys_count','aggressive_count','non_aggressive_count','aggressive_rate_when_present','source_skew_ratio','include_in_mask_group'])
    print('inventory built')
if __name__=='__main__': main()
