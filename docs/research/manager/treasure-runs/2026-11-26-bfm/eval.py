import os,json,hashlib,urllib.request,urllib.parse,re,itertools,math,statistics,random,time,torch
from collections import Counter
from contextlib import nullcontext
from tokenizers import Tokenizer
from transformers import AutoModelForCausalLM
from peft import PeftModel
root=os.path.expanduser('~/.cache/anicca-research-672'); repo='HikaruAsano/cross-psych-101'; rev='532794c51e046a0ddaf560e7972789688d46bf63'
def get(url):
 with urllib.request.urlopen(url,timeout=20) as f:return f.read()
assert json.loads(get('https://huggingface.co/api/datasets/'+repo))['sha']==rev
specs=[(5080,'temporal_discounting','classification',['A','B'],'6aa81eefe9635e06d5e2c9e4d2f12ef56e2aea65d5b0cd00086392c4c43dc194'),(5160,'shuffled_card_task','two_armed_bandit',['safe','risky'],'7baab16f4f3e7f560cb4704c6e3def0b690d70c419029f63132459c2dd205244'),(7080,'ultimatum_game','temporal_discounting',['immediate','delayed'],'d37aff8ce0d8ae8ff735065a4313377d9aaed34386284a562db29d8a42bc303e')]; cases=[]; groups=[]
for off,src,tgt,opts,sha in specs:
 b=get('https://datasets-server.huggingface.co/rows?'+urllib.parse.urlencode(dict(dataset=repo,config='default',split='test',offset=off,length=80))); assert hashlib.sha256(b).hexdigest()==sha; data=json.loads(b); assert data['num_rows_total']==7295; seen=set(); rr=[]
 for e in data['rows']:
  r=e['row']; uid=r['participant']
  if (r['task_type'],r['prev_task_name'],r['next_task_name'])!=('cross_task',src,tgt) or uid in seen:continue
  u,a=r['message']; assert u['role']=='user' and a['role']=='assistant'; u=u['content']; a=a['content']; m=re.search(r'<<(.*?)>>',a)
  if not m or m.group(1) not in opts:continue
  prefix=a[:m.start()]+'<<'
  if '\n' in prefix or len(prefix)>250:continue
  l=u.index('--- PREVIOUS EXPERIMENT DESCRIPTION ---'); end='--- END PREVIOUS EXPERIMENT ---'; h=u.index(end)+len(end); seen.add(uid); rr.append(dict(idx=e['row_idx'],uid=uid,history=u[l:h],pre=u[:l],tail=u[h:],prefix=prefix,label=m.group(1),opts=opts,group=src+'->'+tgt))
  if len(rr)==8:break
 assert len(rr)==8
 perm=next((p for p in itertools.permutations(range(8)) if all(i!=j and rr[i]['history']!=rr[j]['history'] for i,j in enumerate(p))),None); assert perm is not None
 for i,x in enumerate(rr):x['other']=rr[perm[i]]['history'];cases.append(x)
 groups.append(dict(offset=off,sha256=sha,group=rr[0]['group'],row_indices=[x['idx'] for x in rr],labels=dict(Counter(x['label'] for x in rr)),permutation=perm))
print('COHORT',json.dumps(groups),'unique_people',len({x['uid'] for x in cases}),flush=True)
torch.set_num_threads(2); base=root+'/smol-base'; adapter=root+'/smol-adapter'; tok=Tokenizer.from_file(adapter+'/tokenizer.json'); assert tok.get_vocab()==Tokenizer.from_file(base+'/tokenizer.json').get_vocab(); m=PeftModel.from_pretrained(AutoModelForCausalLM.from_pretrained(base,local_files_only=True,dtype=torch.float32),adapter,local_files_only=True).eval(); rows=[]
def score(p,a):
 x=tok.encode(p,add_special_tokens=False).ids;y=tok.encode(p+a,add_special_tokens=False).ids; assert y[:len(x)]==x and len(y)<8192
 ids=torch.tensor([y]); lp=m(ids).logits[0,len(x)-1:-1].float().log_softmax(-1);return float(lp.gather(1,ids[0,len(x):,None]).sum())
start=time.monotonic()
with torch.inference_mode():
 for i,x in enumerate(cases):
  for condition in ('matched','shuffled','none'):
   h=x['history'] if condition=='matched' else x['other'] if condition=='shuffled' else 'No previous experiment information is available.'
   p=x['pre']+h+x['tail']+'\n'+x['prefix']
   for mode in ('base','adapter'):
    with m.disable_adapter() if mode=='base' else nullcontext(): l=[score(p,a) for a in x['opts']]
    k=x['opts'].index(x['label']); prob=torch.softmax(torch.tensor(l),0).tolist(); rows.append(dict(case=i,group=x['group'],condition=condition,model=mode,nll=-math.log(prob[k]),raw_nll=-l[k],brier=(1-prob[k])**2,correct=int(prob[k]>prob[1-k])))
  print('PROGRESS',i+1,len(cases),flush=True)
summary=[]
for mode in ('base','adapter'):
 for condition in ('matched','shuffled','none'):
  a=[r for r in rows if r['model']==mode and r['condition']==condition];summary.append(dict(model=mode,condition=condition,n=len(a),nll=statistics.mean(r['nll'] for r in a),raw_nll=statistics.mean(r['raw_nll'] for r in a),brier=statistics.mean(r['brier'] for r in a),correct=sum(r['correct'] for r in a)))
print('RESULT '+json.dumps(dict(scope='public viewer first-action research probe, not official Psych-101 or Cross-Centaur replication; no raw data export',dataset_revision=rev,groups=groups,n_cases=len(cases),unique_people=len({x['uid'] for x in cases}),forward_passes=2*len(rows),uniform_nll=math.log(2),uniform_brier=.25,seconds=time.monotonic()-start,summary=summary,rows=rows)),flush=True)
