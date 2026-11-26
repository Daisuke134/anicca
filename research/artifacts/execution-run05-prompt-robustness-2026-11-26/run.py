import pathlib,hashlib,json,time,gc
home=pathlib.Path.home();prev=home/'anicca-research-artifacts/execution-run04-invariance';out=home/'anicca-research-artifacts/execution-run05-prompt-robustness';out.mkdir(exist_ok=True)
s=(prev/'run.py').read_text().split('from peft import LoraConfig')[0].replace('execution-run04-invariance','execution-run05-prompt-robustness').replace('tr=ids[2880:2944];va=ids[3136:3200];te=ids[3584:3712];assert len(set(tr+va+te))==256','tr=ids[2880:2944];va=ids[3136:3200];te=ids[3712:3808];assert len(set(tr+va+te))==224')
exec(compile(s,str(prev/'run.py'),'exec'))
start=time.time()
templates=['canonical','english_paraphrase','japanese_question','japanese_full']
def encode(i,swap,k):
 r=data[i];n=[r['Administrative'],r['Informational'],r['ProductRelated'],str(round(float(r['ProductRelated_Duration']))),str(r['VisitorType']=='Returning_Visitor'),r['Weekend']]
 if k=='canonical':return enc(i,swap)
 opts='A: yes\nB: no' if swap else 'A: no\nB: yes'
 if k=='english_paraphrase':p=f'Online shopping session. Administrative pages: {n[0]}. Informational pages: {n[1]}. Product pages: {n[2]}. Product browsing seconds: {n[3]}. Returning visitor: {n[4]}. Weekend: {n[5]}. Was a purchase made by the end of this session? '+opts+'\nAnswer: <<'
 elif k=='japanese_question':p=f'Online shopping session. Administrative pages: {n[0]}. Informational pages: {n[1]}. Product pages: {n[2]}. Product browsing seconds: {n[3]}. Returning visitor: {n[4]}. Weekend: {n[5]}. このセッションの終了時に購入しましたか？ '+opts+'\nAnswer: <<'
 else:
  opts='A: はい\nB: いいえ' if swap else 'A: いいえ\nB: はい'
  p=f'オンラインショッピングのセッション。管理ページ数: {n[0]}。情報ページ数: {n[1]}。商品ページ数: {n[2]}。商品閲覧秒数: {n[3]}。再訪問者: {n[4]}。週末: {n[5]}。このセッションの終了時に購入しましたか？ '+opts+'\nAnswer: <<'
 a=tok.encode(p,add_special_tokens=False).ids;b=[tok.encode(p+c,add_special_tokens=False).ids for c in 'AB'];assert all(x[:-1]==a for x in b);assert [x[-1] for x in b]==choice.tolist();return a,[x[-1] for x in b]
allE={k:{(i,sw):encode(i,sw,k) for i in va+te for sw in [False,True]} for k in templates}
receipt4=json.loads((prev/'receipt.json').read_text());results={}
def apply(p,c):return (c['scale']*torch.logit(p.clamp(1e-7,1-1e-7))+c['bias']).sigmoid()
for name in ['base','weighted_42','dpo_42','dpo_consistency_42']:
 m=AutoModelForCausalLM.from_pretrained(str(base),local_files_only=True,dtype=torch.float32)
 if name!='base':
  assert sha(prev/name/'adapter_model.safetensors')==receipt4['results'][name]['adapter_sha'];m=PeftModel.from_pretrained(m,str(prev/name),local_files_only=True)
 V=[];T=[];gaps={}
 for k in templates:
  E=allE[k];v=infer(m,va);t=infer(m,te);V.append(v.mean(1));T.append(t.mean(1));gaps[k]=float((t[:,0]-t[:,1]).abs().mean())
 v=torch.stack(V);t=torch.stack(T);cp,c=calibrate(v[0],t[0]);ep,ec=calibrate(v.mean(0),t.mean(0));cal=apply(t,c)
 a={'canonical_calibration':c,'ensemble_calibration':ec,'template_metrics':{k:metrics(cal[j],yy) for j,k in enumerate(templates)},'ensemble_metrics':metrics(ep,yy),'raw_shift':{k:float((t[j]-t[0]).abs().mean()) for j,k in enumerate(templates)},'calibrated_shift':{k:float((cal[j]-cal[0]).abs().mean()) for j,k in enumerate(templates)},'order_gap':gaps,'mean_raw_range':float((t.max(0).values-t.min(0).values).mean()),'mean_cal_range':float((cal.max(0).values-cal.min(0).values).mean()),'raw_predictions':t.tolist(),'cal_predictions':cal.tolist(),'ensemble_predictions':ep.tolist(),'calibration_raw_predictions':v.tolist()}
 results[name]=a;print('RESULT',name,json.dumps({k:v for k,v in a.items() if 'predictions' not in k}),flush=True)
 del m;gc.collect();(out/'partial.json').write_text(json.dumps(results,indent=2))
r={'scope':'retrospective prompt stress test, seed42 checkpoints only, no new training; 4 manually authored templates; own-pilot test slice only','templates':templates,'train_n':len(tr),'cal_n':len(va),'cal_positive':int(yv.sum()),'test_n':len(te),'test_positive':int(yy.sum()),'test_indices':te,'test_labels':yy.tolist(),'cal_labels':yv.tolist(),'results':results,'prompt_examples':{k:tok.decode(allE[k][te[0],False][0]) for k in templates},'duration_s':time.time()-start,'prompt_count':4*len(templates)*2*(len(va)+len(te))}
(out/'receipt.json').write_text(json.dumps(r,indent=2,ensure_ascii=False));print('DONE',r['duration_s'],r['prompt_count'],flush=True)

