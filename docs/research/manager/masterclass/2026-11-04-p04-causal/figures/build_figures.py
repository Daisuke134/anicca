"""Reproduce P04-3 figures solely from the checked-in educational results."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent.parent
out=ROOT/'figures'
r=json.loads((ROOT/'evidence/P04-3_SYNTHETIC_RESULTS.json').read_text())

plt.rcParams.update({'font.size':12,'axes.spines.top':False,'axes.spines.right':False})
labels=['Naive observation','Standardization','IPW (Hajek)','AIPW','Imperfect proxy']
keys=['naive_observational_difference','g_formula_standardization','ipw_hajek','aipw_no_crossfitting','imperfect_proxy_adjustment_NOT_IDENTIFIED']
ys=[r[k]*100 for k in keys]
fig,ax=plt.subplots(figsize=(11.8,3.15))
cols=['#c84f45','#087b80','#087b80','#087b80','#c18b30']
ax.barh(labels,ys,color=cols,height=.60)
ax.axvline(-10,color='#243b52',linestyle='--',linewidth=1.4)
ax.text(-10.3,4.49,'Synthetic true ATE = −10 pp',ha='right',fontsize=9,color='#243b52')
for i,v in enumerate(ys):
    ax.text(v+(.7 if v>=0 else -.7),i,f'{v:+.2f} pp',va='center',ha='left' if v>=0 else 'right',fontsize=10)
ax.set_xlim(-23,44);ax.invert_yaxis();ax.set_xlabel('Observed difference / estimated effect (percentage points)',fontsize=10)
fig.tight_layout()
fig.savefig(out/'p04_3_estimates.png',dpi=170,facecolor='white',bbox_inches='tight')
plt.close(fig)

fig,ax=plt.subplots(figsize=(8,4.35))
x=np.array([0,1]);ax.plot(x,[30,38],marker='o',markersize=9,linewidth=3,color='#007a7f',label='Treated group')
ax.plot(x,[20,25],marker='o',markersize=9,linewidth=3,color='#e0a238',label='Comparison group')
ax.plot(x,[30,35],linestyle='--',linewidth=1.6,color='#2a4864',label='Treated counterfactual if parallel')
ax.text(1.01,38,'38%',va='center',fontsize=13);ax.text(1.01,35,'35%',va='center',fontsize=11);ax.text(1.01,25,'25%',va='center',fontsize=13)
ax.set_xlim(-.12,1.25);ax.set_ylim(14,45);ax.set_xticks([0,1],['Before','After']);ax.set_ylabel('Completion rate (%)')
ax.legend(loc='upper left',fontsize=9,frameon=False)
fig.tight_layout();fig.savefig(out/'p04_3_did.png',dpi=170,facecolor='white',bbox_inches='tight');plt.close(fig)
