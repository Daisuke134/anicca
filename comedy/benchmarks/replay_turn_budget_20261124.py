#!/usr/bin/env python3
"""Paired authored text duration probe using local macOS TTS, never a live Voice test."""
import argparse, hashlib, json, os, platform, re, statistics, struct, subprocess, tempfile
from pathlib import Path
import validate_run as vr
import audit_improv_relevance as ir
import check_injury_2min as sc

def pcm_info(path):
    blob=path.read_bytes()
    if blob[:4]!=b'FORM' or blob[8:12] not in (b'AIFF',b'AIFC'):
        raise ValueError('not AIFF')
    pos=12
    while pos+8<=len(blob):
        kind=blob[pos:pos+4]; size=struct.unpack_from('>I',blob,pos+4)[0]
        start=pos+8; end=start+size
        if end>len(blob): raise ValueError('truncated AIFF')
        if kind==b'SSND':
            offset,_=struct.unpack_from('>II',blob,start)
            pcm=blob[start+8+offset:end]
            if not pcm or not any(pcm): raise ValueError('empty or zero PCM')
            return hashlib.sha256(pcm).hexdigest(),len(pcm)
        pos=end+(size%2)
    raise ValueError('no SSND')

def synth(text, voice, rate, folder):
    p=folder/'one.aiff'
    if p.exists(): p.unlink()
    subprocess.run(['/usr/bin/say','-v',voice,'-r',str(rate),'-o',str(p),text],check=True)
    info=subprocess.check_output(['/usr/bin/afinfo',str(p)],text=True)
    match=re.search(r'estimated duration:\s*([\d.]+)\s*sec',info)
    if not match: raise ValueError(info)
    sha,n=pcm_info(p)
    p.unlink()
    return {'duration_s':float(match.group(1)),'pcm_sha256':sha,'pcm_bytes':n}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--voice',default='Kyoko')
    args=ap.parse_args()
    base=Path(__file__).resolve().parent
    data=json.loads(args.data.read_text())
    tasks=data['tasks']; cases=data['cases']
    rows=[{'task_id':c['id'],'candidate':k,'response':c[k]} for c in cases for k in ('short','long')]
    literal=ir.audit(tasks,rows)
    fmt=[{'task_id':r['task_id'],'candidate':r['candidate'],'issues':vr.score(next(t for t in tasks if t['id']==r['task_id']),r['response'])} for r in rows]
    fixed=vr.jsonl(base/'injury-stage-exact-2026-11-23.jsonl')
    stage=[]
    for t in fixed:
        positive=t.get('expected_exact','')
        negative=positive+'住所は？' if positive else 'もしもし。'
        stage.append({'id':t['id'],'positive':positive,'negative':negative,'positive_accepted':not vr.score(t,positive),'negative_rejected':bool(vr.score(t,negative))})
    md=(base.parent/'sagi-injury-help-2min-live.md').read_text()
    turns=sc.extract_dialogues(md)
    results=[]
    with tempfile.TemporaryDirectory(prefix='comedy-tts-') as tmp:
        folder=Path(tmp)
        for r in rows:
            for rate in (180,220):
                takes=[synth(r['response'],args.voice,rate,folder) for _ in range(2)]
                results.append({**r,'rate_setting':rate,'characters':len(r['response']),'takes':takes,'mean_duration_s':statistics.mean(t['duration_s'] for t in takes),'repeat_duration_delta_s':abs(takes[0]['duration_s']-takes[1]['duration_s']),'repeat_pcm_identical':takes[0]['pcm_sha256']==takes[1]['pcm_sha256']})
        stage_audio=[]
        for t in stage:
            if t['positive']:
                takes=[synth(t['positive'],args.voice,200,folder) for _ in range(2)]
                stage_audio.append({'id':t['id'],'rate_setting':200,'takes':takes,'repeat_pcm_identical':takes[0]['pcm_sha256']==takes[1]['pcm_sha256']})
    pairs=[]
    for c in cases:
        for rate in (180,220):
            a,b=[next(r for r in results if r['task_id']==c['id'] and r['candidate']==k and r['rate_setting']==rate) for k in ('short','long')]
            pairs.append({'id':c['id'],'rate_setting':rate,'short_s':a['mean_duration_s'],'long_s':b['mean_duration_s'],'saved_s':b['mean_duration_s']-a['mean_duration_s']})
    report={'run_id':data['run_id'],'environment':{'platform':platform.platform(),'macos':platform.mac_ver()[0],'python':platform.python_version(),'voice':args.voice,'voice_build':None,'engine':'macOS /usr/bin/say','rate_settings':[180,220],'repetitions':2,'duration_method':'afinfo estimated duration; includes any synthesized silence','pcm_method':'SHA256 of AIFF SSND sound bytes'},'format':fmt,'literal_gate':literal,'fixed_stage_synthetic':stage,'script_static':{'issues':sc.check(md),'turns':len(turns),'characters':sum(len(s) for _,s in turns)},'synthetic_tts':results,'synthetic_fixed_line_tts':stage_audio,'paired_duration':pairs,'summary':{'format_passed':sum(not r['issues'] for r in fmt),'lexical_passed':literal['passed'],'fixed_checks_passed':sum(int(t['positive_accepted'])+int(t['negative_rejected']) for t in stage),'tts_files':sum(len(r['takes']) for r in results+stage_audio),'shorter_pairs':sum(r['saved_s']>0 for r in pairs),'pair_count':len(pairs),'mean_saved_s_by_rate':{str(rate):statistics.mean(r['saved_s'] for r in pairs if r['rate_setting']==rate) for rate in (180,220)},'identical_pcm_pairs':sum(r['repeat_pcm_identical'] for r in results+stage_audio),'repeat_pair_count':len(results+stage_audio)},'limitations':{'actual_voice':'NOT_MEASURED','audience_laughter':'NOT_MEASURED','rear_intelligibility':'NOT_MEASURED','role_understanding':'NOT_MEASURED','turn_latency':'NOT_MEASURED','speaker_attribution':'NOT_MEASURED','human_funniness':'NOT_MEASURED','synthetic_tts_not_live':True,'content_match':'author-designed pairs, not blind-rated; same terminal punchline within each pair','audio_retention':'temporary synthetic files deleted; hashes and durations retained'}}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'summary':report['summary'],'paired_duration':pairs,'script_static':report['script_static'],'environment':report['environment'],'stage_audio':stage_audio},ensure_ascii=False))
if __name__=='__main__': main()
