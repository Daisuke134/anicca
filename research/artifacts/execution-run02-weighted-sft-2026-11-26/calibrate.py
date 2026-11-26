# Pilot004: fixed Pilot003 adapters, disjoint calibration and test.
# UCI CC BY4.0 DOI 10.24432/C5F88Q; no raw records exported.
import pathlib,hashlib,urllib.request,zipfile,io,csv,random,json,math,torch,gc,time
from tokenizers import Tokenizer
from transformers import AutoModelForCausalLM
from peft import PeftModel
import torch.nn.functional as F
torch.set_num_threads(2);torch.manual_seed(42)
home=pathlib.Path.home();base=home/'.cache/anicca-research-672/smol-base';p3=home/'anicca-research-artifacts/manager-local-pilot-003';out=home/'anicca-research-artifacts/manager-local-pilot-004';out.mkdir(exist_ok=True)
assert not (out/'receipt.json').exists()
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert sha(base/'model.safetensors')=='a89922be0493cec67987c2c837589592f945087c1c55ff46fdb52707a91a8f20'
weights={'single':'484de8a0af50cbb6898866be27cee27fd0b0ac71ae9d26441cf8380f7eedd08e','mixed':'596e63d5687a1acff8cc1a58739e2490991bf2cd042ae87392d88b4afc030f6e'}
for name,h in weights.items():assert sha(p3/name/'adapter_model.safetensors')==h
with urllib.request.urlopen('https://archive.ics.uci.edu/static/public/468/online+shoppers+purchasing+intention+dataset.zip',timeout=25) as f:z=zipfile.ZipFile(io.BytesIO(f.read()))
raw=z.read(next(x for x in z.namelist() if x.endswith('.csv')));assert hashlib.sha256(raw).hexdigest()=='b3055ee355f59134d851d32641183cb4a8b45def7124d2f50442a042f358e0d9'
data=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))));ids=list(range(len(data)));random.Random(42).shuffle(ids)
tr=ids[1280:1408];va=ids[1472:1600];te=ids[1600:1728];assert len(set(ids[:1728]))==1728
def y(i):return int(data[i]['Revenue']=='TRUE')
yt=torch.tensor([y(i) for i in tr],dtype=torch.float64);yv=torch.tensor([y(i) for i in va],dtype=torch.float64);yy=torch.tensor([y(i) for i in te],dtype=torch.float64)
tok=Tokenizer.from_file(str(base/'tokenizer.json'))
def enc(i,s):
 r=data[i];p='Online shopping session. Administrative pages: '+r['Administrative']+'. Informational pages: '+r['Informational']+'. Product pages: '+r['ProductRelated']+'. Product browsing seconds: '+str(round(float(r['ProductRelated_Duration'])))+'. Returning visitor: '+str(r['VisitorType']=='Returning_Visitor')+'. Weekend: '+r['Weekend']+'. Did the session end in a purchase? '+('A: yes\nB: no' if s else 'A: no\nB: yes')+'\nAnswer: <<'
 a=tok.encode(p,add_special_tokens=False).ids;b=[tok.encode(p+c,add_special_tokens=False).ids for c in 'AB'];assert all(x[:-1]==a for x in b);return a,[x[-1] for x in b]
E={(i,s):enc(i,s) for i in va+te for s in [False,True]};assert len({tuple(x[1]) for x in E.values()})==1;choice=torch.tensor(next(iter(E.values()))[1])
print('PREFLIGHT',len(tr),int(yt.sum()),len(va),int(yv.sum()),len(te),int(yy.sum()),flush=True)
def infer(m,ii):
 res=[];m.eval()
 with torch.no_grad():
  for j in range(0,len(ii),8):
   seq=[E[i,s][0] for i in ii[j:j+8] for s in [False,True]];lens=torch.tensor([len(x) for x in seq]);x=torch.zeros((len(seq),int(lens.max())),dtype=torch.long);mask=torch.zeros_like(x)
   for k,v in enumerate(seq):x[k,:len(v)]=torch.tensor(v);mask[k,:len(v)]=1
   pos,inv=torch.unique(lens-1,sorted=True,return_inverse=True);v=m(input_ids=x,attention_mask=mask,use_cache=False,logits_to_keep=pos).logits[torch.arange(len(seq)),inv,:][:,choice].float();d=(v[:,1]-v[:,0]).reshape(-1,2);res.append(torch.stack([d[:,0],-d[:,1]],1).double().sigmoid())
 return torch.cat(res)
def features(i):
 r=data[i];return [math.log1p(float(r[k])) for k in ['Administrative','Informational','ProductRelated','ProductRelated_Duration']]+[float(r['VisitorType']=='Returning_Visitor'),float(r['Weekend']=='TRUE')]
def metrics(p,y):
 p=p.clamp(1e-7,1-1e-7);bins=[]
 for k in range(5):
  mask=(p>=k/5)&((p<(k+1)/5) if k<4 else (p<=1))
  if mask.any():bins.append({'n':int(mask.sum()),'pred':float(p[mask].mean()),'obs':float(y[mask].mean())})
 # pairwise AUC with half credit for ties
 a=p[y==1];b=p[y==0];auc=float(((a[:,None]>b).double()+.5*(a[:,None]==b).double()).mean())
 return {'n':len(y),'brier':float(((p-y)**2).mean()),'nll':float(F.binary_cross_entropy(p,y)),'accuracy':float(((p>=.5)==y.bool()).double().mean()),'auc':auc,'mean_p':float(p.mean()),'ece5':sum(z['n']*abs(z['pred']-z['obs']) for z in bins)/len(y),'bins':bins}
def calibrate(v,t):
 x=torch.logit(v.clamp(1e-7,1-1e-7));xx=torch.logit(t.clamp(1e-7,1-1e-7));a=torch.tensor(0.,dtype=torch.float64,requires_grad=True);b=torch.tensor(0.,dtype=torch.float64,requires_grad=True);opt=torch.optim.LBFGS([a,b],lr=.5,max_iter=60,line_search_fn='strong_wolfe')
 def closure():
  opt.zero_grad();loss=F.binary_cross_entropy_with_logits(a.exp()*x+b,yv)+.01*(a*a+b*b);loss.backward();return loss
 opt.step(closure);scale=float(a.detach().exp());bias=float(b.detach());return (scale*xx+bias).sigmoid(),{'scale':scale,'bias':bias,'regularization':.01}
pred={};params={};results={};order={};validation={}
prior=torch.full_like(yy,float(yt.mean()));pred['train_prior']=prior;pred['calibration_prior']=torch.full_like(yy,float(yv.mean()))
x=torch.tensor([features(i) for i in tr],dtype=torch.float64);v=torch.tensor([features(i) for i in te],dtype=torch.float64);mu=x.mean(0);sd=x.std(0).clamp_min(1e-6);x=(x-mu)/sd;v=(v-mu)/sd
lr=torch.nn.Linear(6,1,dtype=torch.float64);opt=torch.optim.AdamW(lr.parameters(),lr=.03,weight_decay=.01)
for _ in range(100):
 opt.zero_grad();loss=F.binary_cross_entropy_with_logits(lr(x).flatten(),yt);loss.backward();opt.step()
with torch.no_grad():pred['logistic']=lr(v).flatten().sigmoid()
for name in ['base','single','mixed']:
 m=AutoModelForCausalLM.from_pretrained(str(base),local_files_only=True,dtype=torch.float32)
 if name!='base':m=PeftModel.from_pretrained(m,str(p3/name))
 v=infer(m,va);t=infer(m,te);del m;gc.collect()
 pred[name]=t.mean(1);validation[name]=v.mean(1).tolist()
 pred[name+'_cal'],params[name]=calibrate(v.mean(1),t.mean(1))
 order[name]={'before':float((t[:,0]-t[:,1]).abs().mean()),'after':float(((params[name]['scale']*torch.logit(t.clamp(1e-7,1-1e-7))+params[name]['bias']).sigmoid()[:,0]-(params[name]['scale']*torch.logit(t.clamp(1e-7,1-1e-7))+params[name]['bias']).sigmoid()[:,1]).abs().mean())}
 print('RESULT',name,json.dumps({'raw':metrics(pred[name],yy),'cal':metrics(pred[name+'_cal'],yy),'params':params[name]},ensure_ascii=False),flush=True)
for k,p in pred.items():results[k]=metrics(p,yy)
rng=torch.Generator().manual_seed(20261126);idx=torch.randint(len(yy),(2000,len(yy)),generator=rng)
def paired(a,b):
 d=((pred[a]-yy)**2-(pred[b]-yy)**2);q=d[idx].mean(1);return {'delta_brier_a_minus_b':float(d.mean()),'ci95':[float(x) for x in torch.quantile(q,torch.tensor([.025,.975],dtype=q.dtype))]}
comparisons={name:paired(name,'calibration_prior') for name in ['base_cal','single_cal','mixed_cal','logistic']}
comparisons.update({name+'_raw_vs_cal':paired(name,name+'_cal') for name in ['base','single','mixed']})
receipt={'scope':'retrospective UCI purchase prediction only; Pilot003 adapters fixed; not intervention or general BFM','data_sha256':hashlib.sha256(raw).hexdigest(),'base_sha256':sha(base/'model.safetensors'),'adapter_sha256':weights,'split':'seed42 train1280:1408, calibration1472:1600, test1600:1728; disjoint from own earlier pilot rows, not guaranteed unseen by all team or base pretraining','train_n':len(tr),'train_positive':int(yt.sum()),'cal_n':len(va),'cal_positive':int(yv.sum()),'test_n':len(te),'test_positive':int(yy.sum()),'calibration':params,'results':results,'comparisons':comparisons,'order_diagnostic':order,'test_indices':te,'test_labels':yy.tolist(),'cal_indices':va,'cal_labels':yv.tolist(),'cal_raw':validation,'test_predictions':{k:v.tolist() for k,v in pred.items()}}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');(out/'calibration.json').write_text(json.dumps(params,indent=2)+'\n');print('DONE',json.dumps({'results':{k:{a:b for a,b in v.items() if a!='bins'} for k,v in results.items()},'comparisons':comparisons}),flush=True)

