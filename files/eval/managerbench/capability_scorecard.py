"""Optional capability view of the existing ManagerBench replay. No pooled score."""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from paired_binary import compare_binary

GEMMA_SHA = 'd672b7101376b5d1d4f366cef0f4dda8eff97263799672446807032256a723e1'
ANOMALY_SHA = '3e4b89e9b095cea985a56ffae4a532a975784954ade13d6c3f724cf01b12ba89'
GEMMA_SOURCE = 'https://github.com/Daisuke134/anicca/releases/tag/manager-gemma4-e2b-hillstrom-2026-11-26'
ANOMALY_SOURCE = 'https://github.com/Daisuke134/anicca-ops/blob/45e7efff65849f277ab62082a884936696755a44/files/research-artifacts/behavior-anomaly-2026-11-26/receipt.json'

def pinned(path, digest):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('external receipt digest mismatch')
    return json.loads(raw)

def probability(x):
    if type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1:
        raise ValueError('invalid probability metric')
    return x

def gemma_track(d):
    rows=d['bfm02_rows']; s=d['bfm02']; h=d['hillstrom']
    if len(rows)!=24 or len({r['context_id'] for r in rows})!=24 or h['n']!=1000:
        raise ValueError('unexpected evaluation frame')
    nt=mc=pc=0; mr=pr=0.
    baseline_outcomes={}; candidate_outcomes={}; ids=[]
    for r in rows:
        a,b=probability(r['human_a']),probability(r['human_b'])
        if r['model'] not in ('A','B') or r['baseline'] not in ('A','B'):
            raise ValueError('unexpected choice')
        if a!=b:
            nt+=1; win='A' if a>b else 'B';mc+=r['model']==win;pc+=r['baseline']==win
            case_id=str(r['context_id']); ids.append(case_id)
            baseline_outcomes[case_id]='correct' if r['baseline']==win else 'incorrect'
            candidate_outcomes[case_id]='correct' if r['model']==win else 'incorrect'
            mr+=max(a,b)-(a if r['model']=='A' else b)
            pr+=max(a,b)-(a if r['baseline']=='A' else b)
    if (nt,mc,pc,0)!=(s['n_non_tied'],s['model_correct'],s['prior_correct'],s['model_invalid']) or not nt:
        raise ValueError('choice count mismatch')
    for actual,expected in [(mc/nt,s['model_accuracy']),(pc/nt,s['prior_accuracy']),(mr/nt,s['model_mean_regret']),(pr/nt,s['prior_mean_regret'])]:
        if not math.isclose(actual,expected,abs_tol=1e-12):
            raise ValueError('choice metric mismatch')
    for k in ('brier','auc','accuracy','mean_p_assigned'):
        probability(h[k])
    if type(h['logloss']) not in (int,float) or not math.isfinite(h['logloss']) or h['logloss']<0:
        raise ValueError('invalid logloss')
    if type(h['mean_pred_uplift']) not in (int,float) or not math.isfinite(h['mean_pred_uplift']) or abs(h['mean_pred_uplift'])>1:
        raise ValueError('invalid uplift')
    return {'status':'PILOT_RECEIPT_REPLAY','source':GEMMA_SOURCE,'sha256':GEMMA_SHA,
            'model':'Gemma4-E2B + Hillstrom adapter','humor':{'n_cases':24,'n_non_tied':nt,'accuracy':mc/nt,'prior_accuracy':pc/nt,'regret':mr/nt,'prior_regret':pr/nt, 'paired_non_tied':compare_binary(ids, baseline_outcomes, candidate_outcomes)},
            'intervention_prediction':{'n':h['n'],**{k:h[k] for k in ('brier','auc','accuracy','logloss','mean_p_assigned','mean_pred_uplift')}},
            'limitation':'Hillstrom aggregate only; base metrics not in this asset; no base rank or causal benefit claim.'}

def anomaly_track(d):
    if [d[k] for k in ('train','calibration','normal','authorized_change','synthetic_deviation')]!=[4096,2048,2048,2048,1024]:
        raise ValueError('unexpected synthetic frame')
    metrics={}
    for arm in ('global','entity','entity_context','autoencoder_42','autoencoder_43'):
        metrics[arm]={k:probability(d['results'][arm][k]) for k in ('normal_alert','authorized_change_alert','deviation_alert')}
    return {'status':'SYNTHETIC_DIAGNOSTIC','source':ANOMALY_SOURCE,'sha256':ANOMALY_SHA,
            'metrics':metrics,'limitation':'Known context supplied by generator; not vendor benchmark, Manager inference or live security.'}


BEHAVIOR_SOURCE = 'files/eval/behaviorbench-full-coverage-final-68of68-2026-11-14.json'
BEHAVIOR_SHA = 'eca914913befae3d446ab201b5e13fdc415be451392f2374588b521ebeaf8094'

def valid_count_audit(d):
    rows=d['results']
    if len(rows)!=68:
        raise ValueError('unexpected final-68 frame')
    known=unknown=valid_sum=receipted=0
    missing_by_arm={}
    for key,r in sorted(rows.items()):
        n=r['n_receipted']
        if r['status']!='OK' or type(n) is not int or n<=0 or n!=r['n_expected']:
            raise ValueError('incomplete final-68 receipt')
        receipted+=n
        m=r.get('metadata') or {}
        v=m.get('num_valid_predictions')
        if v is None:
            unknown+=1
            arm=r['arm']
            missing_by_arm[arm]=missing_by_arm.get(arm,0)+1
        else:
            invalid=m.get('num_failed_parses')
            if type(v) is not int or type(invalid) is not int or not 0<=v<=n or not 0<=invalid<=n or v+invalid!=n:
                raise ValueError('inconsistent valid count')
            known+=1;valid_sum+=v
    return {'source':BEHAVIOR_SOURCE,'sha256':BEHAVIOR_SHA,'receipted_arms':len(rows),
            'receipted_predictions':receipted,'known_valid_count_arms':known,
            'unknown_valid_count_arms':unknown,'known_valid_predictions_sum':valid_sum,
            'all_valid_predictions':valid_sum if unknown==0 else None,
            'missing_by_arm':missing_by_arm,
            'limitation':'Receipt coverage is not valid-prediction coverage; unknown is not zero.'}

def build_scorecard(replay, gemma=None, anomaly=None, behavior_root=None):
    counts=Counter(r['family'] for r in replay['rows'])
    return {'schema':'managerbench.capability-view.v1','global_score':None,
            'global_rank':None,'replayed_rows':len(replay['rows']),
            'historical_incomplete_arms':len(replay['incomplete']),
            'replay_family_row_counts':dict(sorted(counts.items())),
            'tracks':{'human_behavior':{'status':'HISTORICAL_RECEIPT_REPLAY','families':dict(sorted(counts.items())), 'final_68_denominator_audit':valid_count_audit(pinned(Path(behavior_root)/BEHAVIOR_SOURCE, BEHAVIOR_SHA)) if behavior_root is not None else None},
                      'gemma_pilot':gemma_track(pinned(gemma,GEMMA_SHA)) if gemma else {'status':'UNMEASURED_IN_THIS_VIEW'},
                      'defensive_anomaly':anomaly_track(pinned(anomaly,ANOMALY_SHA)) if anomaly else {'status':'UNMEASURED_IN_THIS_VIEW'},
                      **{k:{'status':'NOT_INTEGRATED_IN_THIS_VIEW'} for k in ('general_intelligence','social_simulation','culture','memory','agent_execution','multimodal')},
                      'real_product_benefit':{'status':'UNVERIFIED'}},
            'promotion_eligible':False,'limitation':'Receipt replay, not fresh model inference; distinct metrics and denominators cannot be pooled.'}

