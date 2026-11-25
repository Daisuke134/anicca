"""Synthetic oracle check, not human benefit or official OBP execution."""
import numpy as np
from ope_adapter import prepare

rng=np.random.default_rng(42); n=20000
rows=[]; a=rng.random(n)<.5; y=rng.random(n)<np.where(a,.6,.3)
for i in range(n):
    rows.append(dict(id=str(i),candidates=[dict(id='a',kind='reflection',probability=.5),dict(id='n',kind='none',probability=.5)],chosen_id='a' if a[i] else 'n',pscore=.5,target={'a':.8,'n':.2},reward=int(y[i])))
d,m=prepare(rows); w=d['action_dist'][np.arange(n),d['action'],0]/d['pscore']; q=np.tile([.6,.3],(n,1))
dr=(q*d['action_dist'][:,:,0]).sum(1)+w*(d['reward']-q[np.arange(n),d['action']])
print('synthetic oracle',.8*.6+.2*.3,'logging',d['reward'].mean(),'IPW',np.mean(w*d['reward']),'SNIPW',np.mean(w*d['reward'])/w.mean(),'oracle DR',dr.mean(),'diagnostics',m)
