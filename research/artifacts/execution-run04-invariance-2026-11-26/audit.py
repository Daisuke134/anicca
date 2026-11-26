import json,pathlib,random,statistics,math
p=pathlib.Path(__file__).parent;r=json.loads((p/'receipt.json').read_text());y=r['test_labels'];pos=[i for i,v in enumerate(y) if v];neg=[i for i,v in enumerate(y) if not v];models=r['results'];rng=random.Random(20261126)
def auc(p,ps,ns):return sum((p[i]>p[j])+.5*(p[i]==p[j]) for i in ps for j in ns)/(len(ps)*len(ns))
def brier(p,ii):return sum((p[i]-y[i])**2 for i in ii)/len(ii)
for k,v in models.items():
 pred=v['pred'];assert abs(auc(pred,pos,neg)-v['cal']['auc'])<1e-8;assert abs(brier(pred,range(len(y)))-v['cal']['brier'])<1e-8
pairs=[('dpo_consistency_42','dpo_42'),('dpo_consistency_43','dpo_43')];diff={a+'_minus_'+b:{'auc':[],'brier':[]} for a,b in pairs}
for _ in range(2000):
 ps=rng.choices(pos,k=len(pos));ns=rng.choices(neg,k=len(neg));ii=ps+ns
 for a,b in pairs:
  pa,pb=models[a]['pred'],models[b]['pred'];d=diff[a+'_minus_'+b];d['auc'].append(auc(pa,ps,ns)-auc(pb,ps,ns));d['brier'].append(brier(pa,ii)-brier(pb,ii))
out={k:{m:{'lo':sorted(x)[49],'hi':sorted(x)[1949]} for m,x in v.items()} for k,v in diff.items()};o={'scope':'fixed-prediction paired stratified bootstrap 2000 draws; seed-specific, unadjusted; not training uncertainty','verified_models':len(models),'intervals':out};(p/'audit.json').write_text(json.dumps(o,indent=2));print(json.dumps(o),flush=True)
