"""EconSimulacra scheduling-only audit, never deliver real interventions.

Pass --source to a pinned upstream events/base.py, or --excerpt to the exact
EventTrigger class bytes. The latter avoids loading the heavy package and
only supports time triggers. No copied upstream source is distributed here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

REVISION = "aa1302ed9908e487008cdf999ee8607694bddc83"
BLOB = "2b9e62941626f5ed797581ca6c8e584b89b0beaa"
EXCERPT_SHA256 = "b09873303f0350731b42ef527423f1193c12c2d111d351d8141dd20f160a5250"


def load_trigger(path, excerpt=False):
    raw = path.read_bytes()
    if not excerpt:
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if blob != BLOB:
            raise ValueError("upstream Git blob mismatch")
        raw = raw[raw.index(b"class EventTrigger:"):]
    if hashlib.sha256(raw).hexdigest() != EXCERPT_SHA256:
        raise ValueError("upstream class excerpt mismatch")
    ns = {}
    exec("from __future__ import annotations\nimport random\nfrom typing import Any, Optional, Type\n" + raw.decode(), ns)
    return ns["EventTrigger"]


def run(T):
    configs = [{'at': (1,3,5)}, {'every':2}, {'between':(2,4)},
               {'probability':0., 'at':(1,3,5)}, {'probability':1., 'at':(1,3,5)}]
    rng = random.Random(0)
    triggers = [T(c, [], rng) for c in configs]
    counts = [0]*5
    for step in range(1,7):
        for i,t in enumerate(triggers):
            counts[i] += t.check_trigger_after_step(step)
    if counts != [3,3,3,0,3]:
        raise ValueError("upstream trigger-only expectation mismatch")
    results = {}
    for label, p in [('none',0),('half',.5),('all',1)]:
        vals = []
        for seed in range(1000):
            t = T({'at':list(range(21)), 'probability':p}, [], random.Random(seed))
            vals.append(sum(t.check_trigger_after_step(step) for step in range(21)))
        mean, sd = statistics.mean(vals), statistics.stdev(vals)
        margin = 1.96*sd/math.sqrt(len(vals))
        results[label] = dict(seeds=len(vals),mean=mean,sd=sd,min=min(vals),max=max(vals),
                              total=sum(vals),mc_ci95=[mean-margin,mean+margin])
    if results['none']['total'] != 0 or results['all']['total'] != 21000:
        raise ValueError("boundary mismatch")
    t = T({'every':2,'between':(4,6)},[],random.Random(0))
    union = [i for i in range(10) if t.check_trigger_after_step(i)]
    if union != [1,3,4,5,6,7,9]:
        raise ValueError("time union mismatch")
    return dict(upstream_revision=REVISION, excerpt_sha256=EXCERPT_SHA256,
                scope="synthetic schedule-only; no agent response or human outcome",
                expectation_counts=counts, results=results, union_steps=union)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--source', type=Path)
    g.add_argument('--excerpt', type=Path)
    a = p.parse_args()
    print(json.dumps(run(load_trigger(a.source or a.excerpt, excerpt=a.excerpt is not None)), indent=2))
