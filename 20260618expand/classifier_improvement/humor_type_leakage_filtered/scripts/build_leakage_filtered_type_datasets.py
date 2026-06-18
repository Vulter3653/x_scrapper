from _leakage_common import *
def main():
    rows=read_csv(INPUT); out=[]; summ=[]
    for r in rows:
        nr=dict(r); nr['text_original']=r['text']; counts={}
        for name,groups in VARIANTS:
            if name=='original_text': continue
            txt,c=mask_text(r['text'],groups); nr['text_'+name.replace('mask_','mask_')]=txt; counts[name]=c
        out.append(nr)
    # normalize exact requested column names
    for r in out:
        r['text_mask_wendys_brand']=r.get('text_mask_wendys_brand','')
        r['text_mask_brand_product']=r.get('text_mask_brand_product','')
        r['text_mask_brand_product_competitor']=r.get('text_mask_brand_product_competitor','')
        r['text_mask_campaign_product']=r.get('text_mask_campaign_product','')
        r['text_mask_all_leakage_groups']=r.get('text_mask_all_leakage_groups','')
    for name,groups in VARIANTS:
        col='text_original' if name=='original_text' else 'text_'+name.replace('mask_','mask_')
        changed=0; total_masks=0; bch=wch=agch=0
        for r in rows:
            if name=='original_text': c=0; txt=r['text']
            else: txt,c=mask_text(r['text'],groups)
            if c>0:
                changed+=1; total_masks+=c
                if r['source']=='batch1_fortune100': bch+=1
                if r['source']=='wendys_human_type': wch+=1
                if r['humor_type']=='aggressive': agch+=1
        summ.append({'variant':name,'rows':len(rows),'changed_rows':changed,'changed_row_rate':round(changed/len(rows),4),'avg_tokens_removed_or_masked':round(total_masks/len(rows),4),'batch1_changed_rows':bch,'wendys_changed_rows':wch,'aggressive_changed_rows':agch})
    fields=list(read_csv(INPUT)[0].keys())+['text_original','text_mask_wendys_brand','text_mask_brand_product','text_mask_brand_product_competitor','text_mask_campaign_product','text_mask_all_leakage_groups']
    write_csv(DATA/'type_training_leakage_filtered_variants.csv',out,fields)
    write_csv(DIAG/'leakage_filtering_summary.csv',summ,['variant','rows','changed_rows','changed_row_rate','avg_tokens_removed_or_masked','batch1_changed_rows','wendys_changed_rows','aggressive_changed_rows'])
    print('variants built')
if __name__=='__main__': main()
