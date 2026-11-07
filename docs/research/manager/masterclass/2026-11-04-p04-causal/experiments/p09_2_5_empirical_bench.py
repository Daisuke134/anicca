#!/usr/bin/env python3
"""P09-2..5: real-data, held-out low-dimensional behavioral-response models.

DATA PROVENANCE (read-only, files NOT committed):
- Nature 2026 official Figure 1 aggregate effects, 70 studies, 3356 directed rows.
  Input: /tmp/anicca_nature2026_replication/figure1_panelA_effects.csv
- MaMe-Re Japanese manga meme human rating aggregates, 100k context-image pairs.
  Input: source repo CyberAgentAILab/mame-re score.csv, context.csv,
  image.csv (only its CC BY description used; NOT manga images or dialogues).

What is trained: small regression/calibration heads, NOT a new LLM or BFM.
Outcomes have differing meaning and MUST NOT be pooled as a single leaderboard.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

SEED = 20261106
ROOT = Path("/tmp/anicca_p09_eval")
NATURE = Path("/tmp/anicca_nature2026_replication/figure1_panelA_effects.csv")


def read_nature(path=NATURE):
    with Path(path).open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 3356:
        raise ValueError(f"Expected 3356 published plot rows, got {len(rows)}")
    data = defaultdict(list)
    groups = {}
    # Lexicographically choose ONE direction per mirrored contrast: no sign leakage.
    for r in rows:
        if r["reference_condition"] < r["condition"]:
            study = r["study"]
            data[study].append((float(r["prediction"]), float(r["human"])))
            if study in groups and groups[study] != r["group"]:
                raise ValueError("Study has mixed publication-status labels")
            groups[study] = r["group"]
    assert sum(map(len, data.values())) == 1678 and len(data) == 70
    return {k: np.asarray(v, dtype=float) for k, v in data.items()}, groups


def fit_line(by_study, ids):
    """Study-balanced weighted least squares on [1,predicted_effect]."""
    accum = np.zeros((2, 2))
    target = np.zeros(2)
    for s in ids:
        arr = by_study[s]
        x = np.column_stack((np.ones(len(arr)), arr[:, 0]))
        w = 1 / len(arr)
        accum += w * (x.T @ x)
        target += w * (x.T @ arr[:, 1])
    return np.linalg.solve(accum + np.eye(2) * 1e-7, target)


def predict_line(beta, x):
    return beta[0] + beta[1] * x


def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def mae(a, b):
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def stable_rng(label, rep=0):
    seed = int.from_bytes(hashlib.blake2b(f"{SEED}|{label}|{rep}".encode(), digest_size=8).digest(), "little")
    return np.random.default_rng(seed)


def fewshot(by_study, k_values=(0, 1, 3, 5), repetitions=8, lam=5.0):
    """Each heldout study is queried on a fixed 25% holdout; <=5 support pairs."""
    all_ids = sorted(by_study)
    eligible = [s for s in all_ids if len(by_study[s]) >= 8]
    excluded = [s for s in all_ids if s not in eligible]
    models = ["raw", "zero_shot_global"] + [f"partial_pool_k{k}" for k in k_values if k] + [
        f"unpooled_k{k_values[-1]}"
    ]
    study_sq = {m: defaultdict(list) for m in models}
    micro_sq = {m: [] for m in models}
    for study in eligible:
        beta = fit_line(by_study, [s for s in all_ids if s != study])
        arr = by_study[study]
        for rep in range(repetitions):
            perm = stable_rng(study, rep).permutation(len(arr))
            n_query = max(2, int(math.ceil(len(arr) * .25)))
            support = arr[perm[:-n_query]]
            query = arr[perm[-n_query:]]
            px, py = query[:, 0], query[:, 1]
            base = predict_line(beta, px)
            local_resid = support[:, 1] - predict_line(beta, support[:, 0])
            pred_map = {"raw": px, "zero_shot_global": base}
            for k in k_values:
                if k == 0:
                    continue
                bias = float(np.sum(local_resid[:k]) / (k + lam))
                pred_map[f"partial_pool_k{k}"] = base + bias
            k = k_values[-1]
            pred_map[f"unpooled_k{k}"] = base + float(np.mean(local_resid[:k]))
            for name, pred in pred_map.items():
                err = (np.asarray(pred) - py) ** 2
                study_sq[name][study].append(float(np.mean(err)))
                micro_sq[name].extend(err.tolist())
    results = {}
    for name in models:
        macro = [np.mean(study_sq[name][s]) for s in eligible]
        results[name] = {
            "rmse_micro": math.sqrt(float(np.mean(micro_sq[name]))),
            "rmse_study_macro": float(np.mean(np.sqrt(macro))),
            "n_study_folds": len(eligible),
        }
    # Exploratory paired uncertainty: resample whole heldout studies, not rows or 8 repetitions.
    prng = stable_rng("fewshot-macro-bootstrap")
    per_study_delta = np.asarray([
        math.sqrt(float(np.mean(study_sq["zero_shot_global"][sid]))) -
        math.sqrt(float(np.mean(study_sq["partial_pool_k5"][sid])))
        for sid in eligible
    ])
    boot = [float(prng.choice(per_study_delta, len(per_study_delta), replace=True).mean()) for _ in range(2000)]
    paired_uncertainty = {
        "study_macro_rmse_delta_zero_minus_fewshot5": float(per_study_delta.mean()),
        "paired_study_bootstrap_95ci": np.quantile(boot, [.025, .975]).tolist(),
        "studies_improved": int(sum(per_study_delta > 0)),
        "studies_worsened": int(sum(per_study_delta < 0)),
        "exploratory": True
    }
    return dict(description="Nature public figure aggregate *contrasts*: 69-study global fit, k labeled target contrasts, different query contrasts; NOT individual-person few-shot BFM",
                eligible_studies=len(eligible), excluded_small_studies=len(excluded),
                support_k=list(k_values), repetitions=repetitions,
                local_prior_strength=lam, results=results, paired_study_uncertainty=paired_uncertainty)


def split_studies(by_study, label_map):
    pub = sorted(s for s in by_study if label_map[s] == "published")
    unpub = sorted(s for s in by_study if label_map[s] == "unpublished")
    rng = stable_rng("nature-published-splits")
    rng.shuffle(pub)
    assert len(pub) == 40 and len(unpub) == 30
    return pub[:24], pub[24:32], pub[32:], unpub


def concat_studies(data, ids):
    return np.vstack([data[s] for s in ids])


def coverage_report(beta, radius, data, ids, ood_threshold, median_x):
    preds, truth, reject = [], [], []
    per_study_coverage = []
    for s in ids:
        arr = data[s]
        p = predict_line(beta, arr[:, 0])
        e = np.abs(p - arr[:, 1])
        keep = np.abs(arr[:, 0] - median_x) <= ood_threshold
        preds.extend(p.tolist())
        truth.extend(arr[:, 1].tolist())
        reject.extend(keep.tolist())
        per_study_coverage.append(float(np.mean(e <= radius)))
    preds = np.asarray(preds)
    truth = np.asarray(truth)
    keep = np.asarray(reject, dtype=bool)
    return dict(studies=len(ids), pairs=len(preds),
                rmse=rmse(truth, preds),
                interval_halfwidth=radius,
                empirical_pair_coverage=float(np.mean(np.abs(truth-preds) <= radius)),
                empirical_study_macro_coverage=float(np.mean(per_study_coverage)),
                retained_fraction=float(np.mean(keep)),
                retained_rmse=rmse(truth[keep], preds[keep]) if keep.any() else None,
                rejected_count=int((~keep).sum()))


def ood_calibration(by_study, label_map):
    train, cal, id_test, ood_test = split_studies(by_study, label_map)
    beta = fit_line(by_study, train)
    calarr = concat_studies(by_study, cal)
    cal_error = np.abs(calarr[:, 1] - predict_line(beta, calarr[:, 0]))
    radius = float(np.quantile(cal_error, .9, method="higher"))
    tr = concat_studies(by_study, train)[:, 0]
    med = float(np.median(tr))
    cutoff = float(np.quantile(np.abs(tr-med), .9, method="higher"))
    return dict(
        warning="Published/unpublished is publication-status proxy, not a new cultural/domain dataset; no exchangeable conformal validity under shift.",
        train_studies=len(train),calibration_studies=len(cal),in_domain_test_studies=len(id_test),
        out_of_group_studies=len(ood_test),beta=beta.tolist(),
        q90_calibration_error=radius,ood_abs_effect_cutoff=cutoff,
        in_domain=coverage_report(beta,radius,by_study,id_test,cutoff,med),
        unpublished_group=coverage_report(beta,radius,by_study,ood_test,cutoff,med),
        theta_source_line=beta.tolist(),
        study_split_ids={k:v for k,v in dict(train=train,calibration=cal,in_domain_test=id_test,out_of_group=ood_test).items()}
    )


def text_features(text):
    # Character trigram hashed features from CC BY context text only.
    text = (text or "")[:250]
    v = np.zeros(24, dtype=np.float64)
    for i in range(max(0, len(text) - 2)):
        g = text[i:i+3]
        idx = int.from_bytes(hashlib.blake2s(g.encode(), digest_size=2).digest(), "little") % len(v)
        v[idx] += 1
    norm = np.linalg.norm(v)
    return v / norm if norm else v


def read_meme(root=ROOT):
    with (root/"context.csv").open(encoding="utf-8-sig") as f:
        ctxt = {int(r["id"]): r["text"] for r in csv.DictReader(f)}
    with (root/"image.csv").open(encoding="utf-8-sig") as f:
        # Deliberately do not use 'text' or artwork: separate licensed manga dialogue/visual rights.
        descriptions = {int(r["id"]): r["description"] for r in csv.DictReader(f)}
    if set(ctxt) != set(range(250)) or set(descriptions) != set(range(400)):
        raise ValueError("MaMe-Re dataset schema mismatch")
    values = np.full((250, 400), np.nan, dtype=float)
    with (root/"score.csv").open(encoding="utf-8-sig") as f:
        rows = 0
        for rec in csv.DictReader(f):
            i,j,y=int(rec["context_id"]),int(rec["image_id"]),float(rec["score"])
            if not np.isnan(values[i,j]) or not (0 <= y <= 1):
                raise ValueError("Duplicate or out-of-bounds meme pair")
            values[i,j] = y
            rows+=1
    assert rows==100000 and np.isfinite(values).all()
    return values,ctxt,descriptions


def feature_matrix(context_ids, context_text, descriptions):
    ctxs = [context_text[int(i)] for i in context_ids]
    items = [descriptions[i] for i in range(400)]
    # 1 intercept, 24 character trigrams of context, 1 context length,
    # 1 image description length, 1 character-overlap Jaccard.
    X = np.zeros((len(ctxs),400,28),dtype=np.float64)
    descsets=[set(s) for s in items]
    imglen = np.array([min(len(t)/100,3) for t in items])
    for i,txt in enumerate(ctxs):
        X[i,:,0]=1
        X[i,:,1:25]=text_features(txt)
        X[i,:,25]=min(len(txt)/100,3)
        X[i,:,26]=imglen
        cs=set(txt)
        for j,ds in enumerate(descsets):
            size=len(cs|ds)
            X[i,j,27]=len(cs&ds)/size if size else 0
    return X.reshape((-1,28))


def ridge_fit(X,y,alpha):
    gram=X.T@X
    rhs=X.T@y
    p=np.eye(X.shape[1])*alpha
    p[0,0]=alpha*.01
    return np.linalg.solve(gram+p,rhs)


def meme_models(root=ROOT):
    y, ctxt, desc = read_meme(root)
    ids = stable_rng("mame-re-context-holdout").permutation(250)
    train, valid, test=ids[:160],ids[160:200],ids[200:]
    prior = float(y[train].mean())
    img_avg = (y[train].sum(axis=0)+10*prior)/(len(train)+10)
    train_base=np.broadcast_to(img_avg, (len(train),400))
    val_base=np.broadcast_to(img_avg, (len(valid),400))
    test_base=np.broadcast_to(img_avg, (len(test),400))
    Xtr=feature_matrix(train, ctxt, desc)
    Xv=feature_matrix(valid, ctxt, desc)
    Xt=feature_matrix(test, ctxt, desc)
    rtr=(y[train]-train_base).ravel()
    alphas=(1.,10.,100.,1000.)
    candidates=[]
    for alpha in alphas:
        beta=ridge_fit(Xtr,rtr,alpha)
        val_pred=np.clip(val_base.ravel()+Xv@beta,0,1)
        candidates.append((rmse(y[valid].ravel(),val_pred),alpha,beta))
    candidates.sort(key=lambda a:(a[0],a[1]))
    val_error, chosen, beta=candidates[0]
    tst=y[test].ravel()
    global_pred=np.full(len(tst),prior)
    image_pred=test_base.ravel().copy()
    content_pred=np.clip(image_pred+Xt@beta,0,1)
    summaries={
        "global_mean": {"rmse":rmse(tst,global_pred),"mae":mae(tst,global_pred)},
        "image_historical_mean": {"rmse":rmse(tst,image_pred),"mae":mae(tst,image_pred)},
        "text_context_description_ridge": {"rmse":rmse(tst,content_pred),"mae":mae(tst,content_pred)}
    }
    study_risk={}
    for lab,pp in [("global_mean",global_pred),("image_historical_mean",image_pred),("text_context_description_ridge",content_pred)]:
        err=(pp.reshape(50,400)-y[test])**2
        study_risk[lab]=np.sqrt(err.mean(axis=1)).tolist()
    # Bootstrap entire test contexts; pair labels within one context share a design.
    e_image = (image_pred.reshape(50,400)-y[test])**2
    e_content = (content_pred.reshape(50,400)-y[test])**2
    brng=stable_rng("meme-context-bootstrap")
    delta_samples=[]
    for _ in range(2000):
        sampled=brng.integers(0,50,size=50)
        delta_samples.append(float(math.sqrt(e_image[sampled].mean())-math.sqrt(e_content[sampled].mean())))
    paired_uncertainty={
        "image_minus_text_ridge_test_rmse": rmse(tst,image_pred)-rmse(tst,content_pred),
        "context_cluster_bootstrap_95ci":np.quantile(delta_samples,[.025,.975]).tolist(),
        "n_test_contexts":50,
        "exploratory":True
    }
    return dict(
        source="https://github.com/CyberAgentAILab/mame-re",license="CC BY 4.0 for score/context/description only. Manga images/dialogue not used.",
        n_contexts=250,n_meme_items=400,ratings_per_pair=5,n_aggregate_pairs=100000,
        train_contexts=len(train),validation_contexts=len(valid),test_contexts=len(test),
        test_aggregate_pairs=len(test)*400,
        split_seed=SEED, train_ids=sorted(map(int,train)), validation_ids=sorted(map(int,valid)), test_ids=sorted(map(int,test)),
        training_score_mean=prior,selected_ridge_alpha=chosen,validation_ridge_rmse=val_error,
        metrics=summaries,paired_context_uncertainty=paired_uncertainty,
        labels_are_aggregates_not_individual_laughter=True,
        response_model_inputs="previously scored image_id + CC BY context text + CC BY image description; no manga dialogue/images",
        hidden_per_context_rmse=study_risk,
        task_data={'train_img_avg':img_avg,'train_img_leave_one_context_avg':(y[train].sum(axis=0)[None,:]-y[train]+10*prior)/(len(train)-1+10),'train_scores':y[train],'test_scores':y[test],
                   'train_ids':train,'test_ids':test,
                   'test_base':image_pred,'center_mean':prior}
    )


def transfer_experiment(nature, label_map, meme):
    """A *single shared calibration slope* between two different response scales.

    This is intentionally a tiny, transparent capacity baseline, NOT a shared BFM:
    publication-group Nature effect magnitudes vs crowd-rated meme preference.
    """
    tr, _, source_test, _=split_studies(nature,label_map)
    src_tr=concat_studies(nature,tr)
    src_te=concat_studies(nature,source_test)
    # Fit one slope centered using source-domain observations.
    mux,muy=np.mean(src_tr,axis=0)
    sx=src_tr[:,0]-mux
    sy=src_tr[:,1]-muy
    slope_src=float(np.dot(sx,sy)/np.dot(sx,sx))
    yy=meme['task_data']['train_scores'].ravel()
    # Baseline item means from training contexts; no target context labels in this baseline.
    mx=meme['task_data']['train_img_leave_one_context_avg'].ravel()
    tmx=float(np.mean(mx));tmy=float(np.mean(yy))
    dx=mx-tmx;dy=yy-tmy
    slope_meme=float(np.dot(dx,dy)/np.dot(dx,dx))
    # Balanced equal-task rehearsal of one slope.
    slope_replay=(slope_src+slope_meme)/2
    source_centered=src_te[:,0]-mux
    source_y=src_te[:,1]
    meme_x=meme['task_data']['test_base']
    meme_y=meme['task_data']['test_scores'].ravel()
    def domain_metrics(beta):
        return {"source_rmse":rmse(source_y,muy+beta*source_centered),
                "meme_rmse":rmse(meme_y,tmy+beta*(meme_x-tmx))}
    result={
        "model_class":"Shared one-dimensional response calibration slope, with domain-specific offsets (NOT unified BFM)",
        "domain_a":"Nature published social-science survey treatment effects",
        "domain_b":"MaMe-Re Japanese meme human aggregate funniness ratings",
        "source_slope":slope_src,"new_domain_slope":slope_meme,
        "before_learning_new_domain":domain_metrics(slope_src),
        "after_naive_shared_finetuning":domain_metrics(slope_meme),
        "after_equal_task_replay":domain_metrics(slope_replay),
        "separate_specialist_heads":{
            "source_rmse":domain_metrics(slope_src)["source_rmse"],
            "meme_rmse":domain_metrics(slope_meme)["meme_rmse"]},
        "warning":"Axes and human outcome meanings differ. Negative transfer of THIS intentionally undercapacity shared scalar baseline is not evidence about a 7B BFM. Publication status is not cultural domain. Results are observational prediction evaluations, not causal effects of an intervention."
    }
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--nature",type=Path,default=NATURE)
    p.add_argument("--meme",type=Path,default=ROOT)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    nature, labels=read_nature(args.nature)
    p92=fewshot(nature)
    p93=ood_calibration(nature,labels)
    meme=meme_models(args.meme)
    p94=transfer_experiment(nature,labels,meme)
    meme.pop('task_data')
    meme.pop('hidden_per_context_rmse')
    result={
        "status":"REAL_DATA_LIGHTWEIGHT_MODEL_TRAIN_AND_EVAL",
        "as_of":"2026-11-06",
        "random_seed":SEED,
        "readme":"Actual scipy/numpy linear/ridge models run on two distinct public human-response aggregate datasets. No LLM/BeFM/Centaur forward-pass and NO individual-level human data.",
        "input_checksums_sha256": {
            "nature_panelA_normalized_csv": hashlib.sha256(args.nature.read_bytes()).hexdigest(),
            **{f"mame_re_{name}": hashlib.sha256((args.meme/name).read_bytes()).hexdigest()
               for name in ("score.csv","context.csv","image.csv")},
        },
        "nature_fig1": {"source":str(args.nature),"n_studies":len(nature),
                        "n_unordered_aggregate_contrasts":sum(map(len,nature.values()))},
        "p09_2_fewshot_study_effect_adaptation":p92,
        "p09_3_publication_status_shift_and_conformal":p93,
        "p09_4_negative_transfer_shared_scalar":p94,
        "p09_5_meme_distinct_task_holdout":meme,
        "scientific_guards":{
            "individual_human_prediction_trained":False,
            "llm_forward_pass_run":False,
            "new_human_study_run":False,
            "multimodal_bfm_weights_trained":False,
            "publication_status_is_real_domain_shift":False,
            "meme_individual_voter_records_available":False,
            "original_rds_full_reproduced":False,
            "synthetic_outcome_labels_used":False
        }}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    compact={key:{'results':v['results']} if key.startswith('p09_2') else
             {k:val for k,val in v.items() if k not in ('study_split_ids','train_ids','validation_ids','test_ids')} for key,v in result.items() if key.startswith('p09_')}
    print(json.dumps(compact,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()