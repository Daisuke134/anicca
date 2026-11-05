"""Planning assumptions only: no participant data or observed effect."""
import json,math
from statsmodels.stats.power import TTestIndPower
rows=[]
for d in [.30,.35,.40]:
 n=TTestIndPower().solve_power(effect_size=d,alpha=.05,power=.80,ratio=1,alternative='two-sided')
 a=math.ceil(n); r=math.ceil(a/.80)
 rows.append(dict(assumed_standardized_effect=d,continuous_n_per_arm=n,analyzable_per_arm=a,randomized_per_arm=r,randomized_total=2*r))
print(json.dumps(dict(status='PLANNING_ASSUMPTIONS_NOT_OBSERVED_EFFECT',alpha=.05,power=.80,assumed_attrition=.20,scenarios=rows),indent=2))
