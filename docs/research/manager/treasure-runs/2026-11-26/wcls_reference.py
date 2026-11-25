import csv,json,hashlib,sys
import numpy as np
from scipy.stats import t
from pathlib import Path
p=Path(sys.argv[1]); b=p.read_bytes(); assert hashlib.sha256(b).hexdigest()=='56ebc36a4d303092421ba9b0b8790aa10a3a5f0f8c5d55181f2a1e1ec6e64825'
r=list(csv.DictReader(b.decode().splitlines())); d={k:np.array([float(x[k]) for x in r]) for k in r[0]}; mask=d['avail']==1; u=d['userid'][mask]; y=d['jbsteps30.log'][mask]; a=d['send'][mask]-.6; pre=d['jbsteps30pre.log'][mask]; lag=d['jbsteps30.log.lag1'][mask]; day=d['study.day.nogap'][mask]; loc=d['location.homework'][mask]; one=np.ones(len(y)); out={}
for name,X in [('marginal',np.column_stack([one,pre,a])),('lag_adjusted',np.column_stack([one,pre,lag,a])),('time_moderation',np.column_stack([one,pre,day,a,a*day])),('lag_moderation',np.column_stack([one,pre,lag,loc,a,a*lag]))]:
 inv=np.linalg.inv(X.T@X); beta=inv@X.T@y; e=y-X@beta; meat=np.zeros((X.shape[1],X.shape[1]));
 for uid in np.unique(u):
  z=X[u==uid]; v=e[u==uid]; adj=np.linalg.solve(np.eye(len(v))-z@inv@z.T,v); score=z.T@adj; meat+=np.outer(score,score)
 se=np.sqrt(np.diag(inv@meat@inv)); df=len(np.unique(u))-len(beta); q=t.ppf(.975,df); out[name]={'coefficients':beta.tolist(),'se_md':se.tolist(),'ci95':np.column_stack([beta-q*se,beta+q*se]).tolist(),'df':int(df)}
print(json.dumps({'source_sha256':hashlib.sha256(b).hexdigest(),'scope':'official synthetic data; Python reference WCLS independent working correlation and Mancl-DeRouen cluster adjustment, not official R runtime','n_rows':len(r),'available':int(mask.sum()),'participants':len(np.unique(u)),'models':out},indent=2))
