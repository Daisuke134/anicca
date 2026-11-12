"""Reduce an evaluator result JSON to non-dataset fields (CC BY-NC-ND data is
not redistributed): per-item index, raw model output, parsed prediction, plus
the evaluator's own metrics/metadata. Ground truth is re-joined from the local
dataset copy when scoring."""
import json, sys
src, dst, arm, task, shard, offset = sys.argv[1:7]
d = json.load(open(src)); t = d['tasks'][0]
out = {'arm': arm, 'task': task, 'shard': shard, 'offset': int(offset),
       'shard_metrics': t['metrics'], 'metadata': t['metadata'], 'inference_settings': d.get('inference_settings'),
       'predictions': [{'i': int(offset) + j, 'raw_output': p.get('raw_output'), 'parsed_prediction': p.get('parsed_prediction')}
                       for j, p in enumerate(t['predictions'] or []) if isinstance(p, dict)]}
json.dump(out, open(dst, 'w'))
print(arm, task, shard, t['metrics'], t['metadata'])
