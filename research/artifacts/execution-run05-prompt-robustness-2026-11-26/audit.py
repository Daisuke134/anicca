import json,pathlib,random,statistics,math
p=pathlib.Path(__file__).parent;r=json.loads((p/'receipt.json').read_text());y=r['test_labels'];pos=[i for i,v in enumerate(y) if v];neg=[i for i,v in enumerate(y) if not v];rng=random.Random(20261126)
def auc(p,ps,ns):return sum((p[i]>p[j])+.5*(p[i]==p[j]) for i in ps for j in ns)/(len(ps)*len(ns))
def brier(p,ii):return sum((p[i]-y[i])**2 for i in ii)/len(ii)
results={}
for name,v in r['results'].items():
 for k,pred,m in [(k,v['cal_predictions'][j],v['template_metrics'][k]) for j,k in enumerate(r['templates'])]+[('ensemble',v['ensemble_predictions'],v['ensemble_metrics'])]:
  assert abs(auc(pred,pos,neg)-m['auc'])<1e-8;assert abs(brier(pred,range(len(y)))-m['brier'])<1e-8
 a=v['ensemble_predictions'];b=v['cal_predictions'][0];diff=[];br=[]
 for _ in range(2000):
  ps=rng.choices(pos,k=len(pos));ns=rng.choices(neg,k=len(neg));ii=ps+ns;diff.append(auc(a,ps,ns)-auc(b,ps,ns));br.append(brier(a,ii)-brier(b,ii))
 results[name]={'auc_ci':[sorted(diff)[49],sorted(diff)[1949]],'brier_ci':[sorted(br)[49],sorted(br)[1949]]}
# Independent pairwise ordering disagreement; ties count as half disagreement when only one side ties.
def sign(x):return (x>0)-(x<0)
def disagreement(a,b):
 n=len(a);return sum(abs(sign(a[i]-a[j])-sign(b[i]-b[j]))/2 for i in range(n) for j in range(i))/(n*(n-1)/2)
rank={name:{k:disagreement(v['raw_predictions'][0],v['raw_predictions'][j]) for j,k in enumerate(r['templates'])} for name,v in r['results'].items()}
p0=sum(r['cal_labels'])/len(r['cal_labels']);prior={'p':p0,'auc':.5,'brier':brier([p0]*len(y),range(len(y))),'nll':-sum(z*math.log(p0)+(1-z)*math.log(1-p0) for z in y)/len(y)}
print('PRIOR',json.dumps(prior),'RANK',json.dumps(rank),flush=True)
(p/'audit.json').write_text(json.dumps({'scope':'fixed-prediction paired stratified bootstrap; 2000 draws; unadjusted, only 9 positives; not training uncertainty','metric_pairs_verified':40,'ensemble_minus_canonical':results,'rank_disagreement':rank,'calibration_prior':prior},indent=2));print(json.dumps(results),flush=True)
