import pathlib,hashlib
home=pathlib.Path.home(); src=home/'anicca-research-artifacts/manager-local-pilot-004/calibrate.py'
assert hashlib.sha256(src.read_bytes()).hexdigest()=='55677c7cfeabc8b91438e6e76fd05f81018f5c49a8ff5f81912748c62743fa8b'
s=src.read_text().split('pred={};params={}')[0].replace("manager-local-pilot-004';out.mkdir","execution-run02-weighted-sft';out.mkdir").replace('tr=ids[1280:1408];va=ids[1472:1600];te=ids[1600:1728];assert len(set(ids[:1728]))==1728','tr=ids[2880:3136];va=ids[3136:3264];te=ids[3264:3520];assert len(set(ids[:3520]))==3520').replace('for i in va+te','for i in tr+va+te')
exec(compile(s,str(src),'exec'))
from peft import LoraConfig,get_peft_model
start=time.time()
def fresh():return AutoModelForCausalLM.from_pretrained(str(base),local_files_only=True,dtype=torch.float32)
pred={'prior':torch.full_like(yy,float(yv.mean()))}; params={}; order={}; adapters={}; trainlogs={}
x=torch.tensor([features(i) for i in tr],dtype=torch.float64);z=torch.tensor([features(i) for i in te],dtype=torch.float64);mu=x.mean(0);sd=x.std(0).clamp_min(1e-6);x=(x-mu)/sd;z=(z-mu)/sd
lr=torch.nn.Linear(6,1,dtype=torch.float64);opt=torch.optim.AdamW(lr.parameters(),lr=.03,weight_decay=.01)
for _ in range(100):
 opt.zero_grad();loss=F.binary_cross_entropy_with_logits(lr(x).flatten(),yt);loss.backward();opt.step()
with torch.no_grad():pred['logistic']=lr(z).flatten().sigmoid()
for name in ['base','standard','weighted']:
 torch.manual_seed(42);m=fresh(); losses=[]
 if name!='base':
  m=get_peft_model(m,LoraConfig(r=4,lora_alpha=8,target_modules=['q_proj','v_proj'],lora_dropout=0,task_type='CAUSAL_LM'));m.train()
  opt=torch.optim.AdamW([p for p in m.parameters() if p.requires_grad],lr=3e-4,weight_decay=0)
  posweight=float((len(tr)-yt.sum())/yt.sum()) if name=='weighted' else 1.
  for j in range(0,len(tr),8):
   ii=tr[j:j+8];seq=[E[i,s][0] for i in ii for s in [False,True]];lens=torch.tensor([len(v) for v in seq]);xx=torch.zeros((len(seq),int(lens.max())),dtype=torch.long);mask=torch.zeros_like(xx)
   for k,v in enumerate(seq):xx[k,:len(v)]=torch.tensor(v);mask[k,:len(v)]=1
   pos,inv=torch.unique(lens-1,sorted=True,return_inverse=True);v=m(input_ids=xx,attention_mask=mask,use_cache=False,logits_to_keep=pos).logits[torch.arange(len(seq)),inv,:][:,choice].float();d=(v[:,1]-v[:,0]).reshape(-1,2);sem=torch.stack([d[:,0],-d[:,1]],1)
   label=torch.tensor([y(i) for i in ii],dtype=torch.float32)[:,None].expand_as(sem)
   loss=F.binary_cross_entropy_with_logits(sem,label,pos_weight=torch.tensor(posweight));opt.zero_grad();loss.backward();opt.step();losses.append(float(loss.detach()))
   if (j//8+1)%8==0:print('STEP',name,j//8+1,losses[-1],flush=True)
  m.save_pretrained(out/name);adapters[name]=sha(out/name/'adapter_model.safetensors');trainlogs[name]={'losses':losses,'posweight':posweight}
 v=infer(m,va);t=infer(m,te);pred[name]=t.mean(1);pred[name+'_cal'],params[name]=calibrate(v.mean(1),t.mean(1));order[name]=float((t[:,0]-t[:,1]).abs().mean())
 print('RESULT',name,json.dumps(metrics(pred[name+'_cal'],yy)),flush=True)
 if name!='base':
  del m,opt;gc.collect();m=PeftModel.from_pretrained(fresh(),str(out/name),local_files_only=True);rr=infer(m,te);trainlogs[name]['reload_delta']=float((rr-t).abs().max());assert trainlogs[name]['reload_delta']<1e-6
 del m;gc.collect()
results={k:metrics(v,yy) for k,v in pred.items()}
ix=torch.randint(len(yy),(5000,len(yy)),generator=torch.Generator().manual_seed(20261126));pairs={}
for a,b in [('weighted_cal','standard_cal'),('weighted_cal','base_cal'),('standard_cal','base_cal'),('weighted_cal','logistic'),('standard_cal','logistic')]:
 d=(pred[a]-yy)**2-(pred[b]-yy)**2;pairs[a+'_minus_'+b]={'delta':float(d.mean()),'ci95':torch.quantile(d[ix].mean(1),torch.tensor([.025,.975],dtype=torch.float64)).tolist()}
r=dict(scope='retrospective UCI class-weighted binary choice SFT; not DPO, causal or official psych benchmark; fresh own-pilot split only',source_sha=sha(src),data_sha=hashlib.sha256(raw).hexdigest(),base_sha=sha(base/'model.safetensors'),adapter_sha=adapters,split='seed42 train2880:3136 cal3136:3264 test3264:3520',train_n=len(tr),train_positive=int(yt.sum()),cal_n=len(va),cal_positive=int(yv.sum()),test_n=len(te),test_positive=int(yy.sum()),calibration=params,results=results,order_gap=order,paired_brier=pairs,trainlogs=trainlogs,test_indices=te,test_labels=yy.tolist(),test_predictions={k:p.tolist() for k,p in pred.items()},duration_s=time.time()-start)
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print('DONE',json.dumps({k:v for k,v in r.items() if k not in ['test_indices','test_labels','test_predictions','trainlogs']}),flush=True)

