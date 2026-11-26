import json,pathlib,random,statistics
p=pathlib.Path(__file__).parent;r=json.loads((p/'receipt.json').read_text());y=r['test_labels'];pos=[i for i,v in enumerate(y) if v];neg=[i for i,v in enumerate(y) if not v];rng=random.Random(20261126)
def auc(p,ps,ns):return sum((p[i]>p[j])+.5*(p[i]==p[j]) for i in ps for j in ns)/(len(ps)*len(ns))
def brier(p,ii):return sum((p[i]-y[i])**2 for i in ii)/len(ii)
m=r['results'];count=0
for name,v in m.items():
 for j,(k,z) in enumerate(v['metrics'].items()):
  pred=v['predictions'][j];assert abs(auc(pred,pos,neg)-z['auc'])<1e-8;assert abs(brier(pred,range(len(y)))-z['brier'])<1e-8;count+=2
out={}
for seed in [42,43]:
 a,b=m[f'joint_{seed}'],m[f'augmentation_{seed}'];diff={k:[] for k in ['held_en','held_ja','raw_range']}
 for _ in range(2000):
  ps=rng.choices(pos,k=len(pos));ns=rng.choices(neg,k=len(neg));ii=ps+ns
  for j,k in enumerate(r['test_keys']):
   if k in diff:diff[k].append(auc(a['predictions'][j],ps,ns)-auc(b['predictions'][j],ps,ns))
  diff['raw_range'].append(sum((max(v[i] for v in a['raw_predictions'])-min(v[i] for v in a['raw_predictions']))-(max(v[i] for v in b['raw_predictions'])-min(v[i] for v in b['raw_predictions'])) for i in ii)/len(ii))
 out[str(seed)]={k:[sorted(v)[49],sorted(v)[1949]] for k,v in diff.items()}
o={'scope':'fixed-prediction unadjusted paired stratified bootstrap, 2000 draws per seed, not training uncertainty','metrics_verified':count,'joint_minus_augmentation_ci':out};(p/'audit.json').write_text(json.dumps(o,indent=2));print(json.dumps(o),flush=True)
