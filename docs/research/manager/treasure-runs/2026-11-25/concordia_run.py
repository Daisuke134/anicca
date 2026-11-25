"""Reproduction wrapper for upstream Concordia resource_dilemma, synthetic only.
Equivalent configuration to the 24-token run; CLI refactor not re-run here.
Run from the pinned upstream checkout with Ollama server on a local address.
"""
import argparse
import itertools
import json
import runpy
import sys
import threading
import time
import types
import ollama
from concordia.contrib.language_models.ollama.ollama_model import OllamaLanguageModel


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output-dir', required=True)
    a=p.parse_args()
    m=types.ModuleType('sentence_transformers')
    def forbidden(*a,**k):
        raise RuntimeError('embedding constructor disabled')
    m.SentenceTransformer=forbidden
    sys.modules['sentence_transformers']=m
    original=ollama.Client.generate
    counter=itertools.count(1)
    lock=threading.Lock()
    start=time.monotonic()
    def bounded(self,*a,**k):
        call=next(counter)
        if time.monotonic()-start>240 or call>180:
            raise RuntimeError('experiment budget reached')
        k['options']={**(k.get('options') or {}),'num_predict':24,'num_ctx':2048}
        r=original(self,*a,**k)
        with lock:
            print('MODEL_RECEIPT',json.dumps({'call':call,'eval_count':r.eval_count,'prompt_eval_count':r.prompt_eval_count,'response':r.response}),flush=True)
        return r
    def constrained(self,prompt,responses,*,seed=None):
        opts=list(responses)
        schema={'type':'object','properties':{'choice':{'type':'string','enum':opts}},'required':['choice'],'additionalProperties':False}
        r=self._client.generate(model=self._model_name,prompt=prompt+'\nChoose exactly one option: '+json.dumps(opts),format=schema,options={'temperature':0,'seed':42 if seed is None else seed},keep_alive='5m')
        v=json.loads(r.response)['choice']
        if v not in opts:
            raise ValueError('invalid choice; no fallback')
        return opts.index(v),v,{}
    ollama.Client.generate=bounded
    OllamaLanguageModel.sample_choice=constrained
    sys.argv=['run','--api_type=ollama','--model_name=smollm2:135m','--use_dummy_embedder','--scenario=network','--num_cycles=1','--output_dir='+a.output_dir,'--seed=42']
    runpy.run_module('examples.resource_dilemma.run',run_name='__main__')


if __name__=='__main__':
    main()
