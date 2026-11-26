import pathlib,hashlib
home=pathlib.Path.home()
src=home/'anicca-research-artifacts/manager-local-pilot-004/calibrate.py'
assert hashlib.sha256(src.read_bytes()).hexdigest()=='55677c7cfeabc8b91438e6e76fd05f81018f5c49a8ff5f81912748c62743fa8b'
s=src.read_text().split('pred={};params={}')[0].replace("manager-local-pilot-004';out.mkdir","execution-run03-dpo-smoke';out.mkdir").replace('tr=ids[1280:1408];va=ids[1472:1600];te=ids[1600:1728];assert len(set(ids[:1728]))==1728','tr=ids[2880:2912];va=ids[3136:3200];te=ids[3520:3584];assert len(set(tr+va+te))==160').replace('for i in va+te','for i in tr+va+te')
exec(compile(s,str(src),'exec'))
from peft import LoraConfig,get_peft_model
start=time.time()
def fresh():return AutoModelForCausalLM.from_pretrained(str(base),local_files_only=True,dtype=torch.float32)
def logits(m,ii):
 seq=[E[i,s][0] for i in ii for s in [False,True]]
 lens=torch.tensor([len(v) for v in seq]);xx=torch.zeros((len(seq),int(lens.max())),dtype=torch.long);mask=torch.zeros_like(xx)
 for k,v in enumerate(seq):xx[k,:len(v)]=torch.tensor(v);mask[k,:len(v)]=1
 pos,inv=torch.unique(lens-1,sorted=True,return_inverse=True);v=m(input_ids=xx,attention_mask=mask,use_cache=False,logits_to_keep=pos).logits[torch.arange(len(seq)),inv,:][:,choice].float()
 d=(v[:,1]-v[:,0]).reshape(-1,2);return torch.stack([d[:,0],-d[:,1]],1)
def ref(m):
 m.eval()
 with torch.no_grad():return {i:d for j in range(0,len(tr),8) for i,d in zip(tr[j:j+8],logits(m,tr[j:j+8]))}
def assess(m):
 v=infer(m,va);t=infer(m,te);p,cal=calibrate(v.mean(1),t.mean(1));return dict(raw=metrics(t.mean(1),yy),cal=metrics(p,yy),order_gap=float((t[:,0]-t[:,1]).abs().mean()),pred=p.tolist(),calibration=cal)
m=fresh();base_ref=ref(m);results={'base':assess(m)};del m;gc.collect()
x=torch.tensor([features(i) for i in tr],dtype=torch.float64);z=torch.tensor([features(i) for i in te],dtype=torch.float64);mu=x.mean(0);sd=x.std(0).clamp_min(1e-6);x=(x-mu)/sd;z=(z-mu)/sd
torch.manual_seed(42);lr=torch.nn.Linear(6,1,dtype=torch.float64);opt=torch.optim.AdamW(lr.parameters(),lr=.03,weight_decay=.01)
for _ in range(100):
 opt.zero_grad();loss=F.binary_cross_entropy_with_logits(lr(x).flatten(),yt);loss.backward();opt.step()
with torch.no_grad():results['logistic']={'cal':metrics(lr(z).flatten().sigmoid(),yy)}
for seed in [42,43]:
 for name in ['sft','weighted','dpo','sft_dpo']:
  torch.manual_seed(seed);m=get_peft_model(fresh(),LoraConfig(r=4,lora_alpha=8,target_modules=['q_proj','v_proj'],lora_dropout=0,task_type='CAUSAL_LM'));opt=torch.optim.AdamW([p for p in m.parameters() if p.requires_grad],lr=3e-4,weight_decay=0)
  order=list(tr);random.Random(seed).shuffle(order);rr=base_ref;losses=[]
  for step in range(4):
   if name=='sft_dpo' and step==2:rr=ref(m)
   m.train();ii=order[step*8:step*8+8];d=logits(m,ii);label=torch.tensor([y(i) for i in ii],dtype=torch.float32)[:,None].expand_as(d)
   if name=='dpo' or (name=='sft_dpo' and step>=2):
    r=torch.stack([rr[i] for i in ii]);loss=-F.logsigmoid(.1*(2*label-1)*(d-r)).mean()
   else:loss=F.binary_cross_entropy_with_logits(d,label,pos_weight=torch.tensor(float((len(tr)-yt.sum())/yt.sum()) if name=='weighted' else 1.))
   opt.zero_grad();loss.backward();opt.step();losses.append(float(loss.detach()))
  key=f'{name}_{seed}';m.save_pretrained(out/key);a=assess(m);a['losses']=losses;a['adapter_sha']=sha(out/key/'adapter_model.safetensors');results[key]=a
  print('RESULT',key,a['cal']['auc'],a['cal']['brier'],a['order_gap'],flush=True)
  del m,opt;gc.collect()
  (out/'partial.json').write_text(json.dumps(results,indent=2))
r=dict(scope='four-step smoke test; two seeds; own-pilot split only; DPO on observed action, not normative preference',train_n=len(tr),train_positive=int(yt.sum()),cal_n=len(va),cal_positive=int(yv.sum()),test_n=len(te),test_positive=int(yy.sum()),test_indices=te,test_labels=yy.tolist(),results=results,duration_s=time.time()-start)
(out/'receipt.json').write_text(json.dumps(r,indent=2));print('DONE',r['duration_s'],flush=True)

