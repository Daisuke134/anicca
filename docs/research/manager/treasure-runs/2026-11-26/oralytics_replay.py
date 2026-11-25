import sys,types, pathlib, json, numpy as np
root=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(root)); pkg=types.ModuleType('rl_ohrs'); pkg.__path__=[str(root/'rl_ohrs')]; sys.modules['rl_ohrs']=pkg
# bypass Flask initialization and private DB only, never deliver real prompts
m=types.ModuleType('rl_ohrs.database.data_tables_integration');
from rl_ohrs.global_vars import PRIOR_MU,PRIOR_SIGMA
m.get_posterior_values=lambda:(0,PRIOR_MU.copy(),PRIOR_SIGMA.copy()); sys.modules[m.__name__]=m
from rl_ohrs.bayes_lr import BayesianLinearRegression,update_posterior
from rl_ohrs.reward_definition import get_reward_components,calculate_a_bar,calculate_b_bar,normalize_a_bar,normalize_b_bar
from rl_ohrs.smoothing_function import L_min,L_max
rng=np.random.default_rng(42); np.random.seed(42); alg=BayesianLinearRegression(); states=[]; actions=[]; probs=[]; rewards=[]; quality=[]; updates=[]; replay_ok=0; hist_a=[0]*14; hist_b=[90]*14
for i in range(140):
 a_bar=normalize_a_bar(calculate_a_bar(np.array(hist_a[-14:]))); b_bar=normalize_b_bar(calculate_b_bar(np.array(hist_b[-14:]))); state=np.array([i%2,b_bar,a_bar,1,1]); a,p,seed=alg.action_selection(state); assert L_min-1e-12<=p<=L_max+1e-12; replay_ok+=int(np.random.default_rng(seed).binomial(1,p)==a)
 # synthetic environment, NOT clinical data: response depends on action and history
 duration=float(np.clip(100+15*a-20*max(a_bar,0)+rng.normal(0,12),0,180)); pressure=5.; comp=get_reward_components(duration,pressure,a,b_bar,a_bar); q=float(comp['quality']); rew=float(comp['reward']); states.append(state); actions.append(int(a)); probs.append(float(p)); rewards.append(rew); quality.append(q); hist_a.append(a); hist_b.append(q)
 if (i+1)%14==0:
  mean,var=update_posterior(np.array(states),np.array(actions),np.array(probs),np.array(rewards)); assert np.all(np.isfinite(mean)) and np.linalg.eigvalsh(var).min()>0; alg.posterior_mean=mean; alg.posterior_var=var; updates.append({'decision':i+1,'mean_probability':float(np.mean(probs[-14:])),'mean_reward':float(np.mean(rewards[-14:]))})
print(json.dumps({'scope':'actual upstream Bayesian update/action/reward functions; synthetic 70-day trajectory; Flask/DB import seams; not service E2E or clinical replication','seed':42,'decisions':len(actions),'posterior_updates':len(updates),'action_count':sum(actions),'replay_ok':replay_ok,'min_probability':min(probs),'max_probability':max(probs),'mean_reward':float(np.mean(rewards)),'mean_quality':float(np.mean(quality)),'updates':updates},indent=2))
