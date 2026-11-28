import pathlib,json,urllib.request,hashlib,re,math,random,time,gc,torch
from transformers import AutoModelForCausalLM,AutoTokenizer
from peft import PeftModel,LoraConfig,get_peft_model
import torch.nn.functional as F
torch.set_num_threads(2);torch.manual_seed(42);random.seed(42)
h=pathlib.Path.home();c=h/'.cache/anicca-research-672';p=h/'anicca-research-artifacts/manager-local-pilot-005'
def sha(f):return hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest()
u='https://datasets-server.huggingface.co/rows?dataset=marcelbinz%2FPsych-201-discrete&config=default&split=train&offset=0&length=100'
raw=urllib.request.urlopen(u,timeout=20).read();source_sha=hashlib.sha256(raw).hexdigest();assert source_sha=='d5a4c1eaab1a7d83be3a3951079c5679712903aa5aa0d521257302607c39c02f'
rows=[];seen=set()
for r in json.loads(raw)['rows']:
 x=r['row']
 if x['experiment']!='ruggeri2022globalizability/exp1.csv' or x['participant'] in seen:continue
 seen.add(x['participant']);s=x['text'];opts=re.search(r'between two options ([A-Z]) and ([A-Z])',s).groups()
 lines=[]
 for line in s.splitlines():
  if not line.startswith('You have the choice'):continue
  a=re.search(r'<<([A-Z])>>',line);assert a and a[1] in opts
  # Canonical option labels, preserve stimulus and map the observed response.
  line=re.sub(r'\(press ([A-Z])\)',lambda m:'(press '+('AB'[opts.index(m[1])])+')',line)
  line=re.sub(r'<<([A-Z])>>',lambda m:'<<'+'AB'[opts.index(m[1])]+'>>',line)
  lines.append(line)
 if len(lines)>=8:rows.append((r['row_idx'],lines[:8]))
del raw,r,x,seen,s
assert len(rows)==20
train=rows[:12];test=rows[12:];assert not set(x[0] for x in train)&set(x[0] for x in test)
t=AutoTokenizer.from_pretrained(c/'smol-base',local_files_only=True);t.padding_side='left';t.pad_token=t.pad_token or t.eos_token
head='Choose between options A and B by pressing the corresponding key.\n\n'
def make(row,other,mode,j):
 idx,lines=row;gold=re.search(r'<<([AB])>>',lines[j])[1];prefix=lines[j].split('<<')[0]+'<<'
 hist=lines[:j] if mode=='own' else other[1][:j] if mode=='other' else []
 txt=head+('\n'.join(hist)+'\n' if hist else '')+prefix
 ids=t(txt,add_special_tokens=False).input_ids;choices=[]
 for o in 'AB':
  full=t(txt+o,add_special_tokens=False).input_ids;assert full[:-1]==ids;choices.append(full[-1])
 assert len(ids)<=512 and len(set(choices))==2
 return dict(row=idx,trial=j,mode=mode,ids=ids,choices=choices,gold='AB'.index(gold))
tr=[make(row,row,'own',j) for row in train for j in range(4,8)]
te=[make(row,test[(i+1)%len(test)],mode,j) for i,row in enumerate(test) for j in range(4,8) for mode in ['own','other','none']]
assert len(tr)==48 and len(te)==96
def load():return AutoModelForCausalLM.from_pretrained(c/'smol-base',local_files_only=True,dtype=torch.float32)
def logits(m,b):
 enc=t.pad({'input_ids':[x['ids'] for x in b]},padding=True,return_tensors='pt')
 pos=enc['attention_mask'].cumsum(1)-1;pos.masked_fill_(enc['attention_mask']==0,0)
 z=m(**enc,position_ids=pos,use_cache=False).logits[:,-1,:]
 return z.gather(1,torch.tensor([x['choices'] for x in b]))
def evaluate(m):
 m.eval();rr=[]
 with torch.inference_mode():
  for k in range(0,len(te),8):
   b=te[k:k+8];v=logits(m,b).double().softmax(1)
   for x,q in zip(b,v):
    g=x['gold'];rr.append(dict(row=x['row'],trial=x['trial'],mode=x['mode'],p_gold=float(q[g]),correct=int(q.argmax()==g)))
 return rr
start=time.monotonic();res={}
m=load();res['base']=evaluate(m);del m;gc.collect();print('base done',flush=True)
m=PeftModel.from_pretrained(load(),c/'smol-adapter',local_files_only=True);res['smoltaur']=evaluate(m);del m;gc.collect();print('smoltaur done',flush=True)
m=PeftModel.from_pretrained(load(),p/'adapter',local_files_only=True);res['pilot005']=evaluate(m);del m;gc.collect();print('pilot done',flush=True)
m=get_peft_model(load(),LoraConfig(r=4,lora_alpha=8,target_modules=['q_proj','v_proj'],lora_dropout=0,task_type='CAUSAL_LM'))
opt=torch.optim.AdamW([v for v in m.parameters() if v.requires_grad],lr=3e-4);losses=[];m.train()
for epoch in range(2):
 order=list(range(len(tr)));random.Random(42+epoch).shuffle(order)
 for k in range(0,len(order),8):
  b=[tr[i] for i in order[k:k+8]]
  loss=F.cross_entropy(logits(m,b),torch.tensor([x['gold'] for x in b]))
  opt.zero_grad();loss.backward();opt.step();losses.append(float(loss.detach()))
 print('epoch',epoch,losses[-6:],flush=True)
res['trained']=evaluate(m);m.save_pretrained('adapter');del m;gc.collect()
m=PeftModel.from_pretrained(load(),'adapter',local_files_only=True);reload=evaluate(m);assert max(abs(a['p_gold']-b['p_gold']) for a,b in zip(reload,res['trained']))<1e-7
def met(rr):return dict(n=len(rr),nll=sum(-math.log(x['p_gold']) for x in rr)/len(rr),accuracy=sum(x['correct'] for x in rr)/len(rr),brier=sum((1-x['p_gold'])**2 for x in rr)/len(rr))
metrics={n:{mode:met([x for x in rr if x['mode']==mode]) for mode in ['own','other','none']} for n,rr in res.items()}
def paired(a,b,ma,mb):
 d=[]
 for idx,_ in test:
  x=[-math.log(r['p_gold']) for r in res[a] if r['row']==idx and r['mode']==ma];y=[-math.log(r['p_gold']) for r in res[b] if r['row']==idx and r['mode']==mb];assert len(x)==len(y)==4;d.append(sum(a-b for a,b in zip(x,y))/4)
 rng=random.Random(42);bs=sorted(sum(rng.choices(d,k=len(d)))/len(d) for _ in range(2000));return [sum(d)/len(d),bs[50],bs[1949]]
ci={'trained_vs_base_own':paired('trained','base','own','own'),'trained_vs_smolt_own':paired('trained','smoltaur','own','own'),'trained_own_vs_other':paired('trained','trained','own','other')}
out=dict(scope='same-task public train split diagnostic, NOT Cross-Centaur official or cross-task; train first12 test last8 distinct participant rows; previously examined train cohort; upstream train exposure unknown; no demographic/clinical/raw transcripts saved',source_sha=source_sha,base_sha=sha(c/'smol-base/model.safetensors'),adapter_sha=sha('adapter/adapter_model.safetensors'),train_rows=[x[0] for x in train],test_rows=[x[0] for x in test],training_steps=len(losses),train_examples=len(tr),losses=losses,metrics=metrics,paired_cluster_ci=ci,eval_forward_examples=480,reload_verified=True,elapsed=time.monotonic()-start)
pathlib.Path('receipt.json').write_text(json.dumps(out,indent=2)+'\n');print('DONE',json.dumps(out),flush=True)
