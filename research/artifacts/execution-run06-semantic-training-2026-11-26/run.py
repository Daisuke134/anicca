import pathlib,hashlib,json,time,gc
home=pathlib.Path.home();prev=home/'anicca-research-artifacts/execution-run04-invariance';out=home/'anicca-research-artifacts/execution-run06-semantic-training';out.mkdir(exist_ok=True)
s=(prev/'run.py').read_text().split('from peft import LoraConfig')[0].replace('execution-run04-invariance','execution-run06-semantic-training').replace('tr=ids[2880:2944];va=ids[3136:3200];te=ids[3584:3712];assert len(set(tr+va+te))==256','tr=ids[2880:2912];va=ids[3200:3232];te=ids[3808:3872];assert len(set(tr+va+te))==128')
exec(compile(s,str(prev/'run.py'),'exec'))
from peft import LoraConfig,get_peft_model
start=time.time()
questions={'canonical':'Did the session end in a purchase?', 'train_en':'Was a purchase made by the end of this session?', 'train_ja':'このセッションの終了時に購入しましたか？','held_en':'At the end of this shopping session, did the visitor buy anything?', 'held_ja':'このオンライン買い物セッションは購入して終了しましたか？'}
train_keys=['canonical','train_en','train_ja'];test_keys=['canonical','held_en','held_ja']
def encode(i,sw,k):
 r=data[i];p='Online shopping session. Administrative pages: '+r['Administrative']+'. Informational pages: '+r['Informational']+'. Product pages: '+r['ProductRelated']+'. Product browsing seconds: '+str(round(float(r['ProductRelated_Duration'])))+'. Returning visitor: '+str(r['VisitorType']=='Returning_Visitor')+'. Weekend: '+r['Weekend']+'. '+questions[k]+' '+('A: yes\nB: no' if sw else 'A: no\nB: yes')+'\nAnswer: <<'
 a=tok.encode(p,add_special_tokens=False).ids;b=[tok.encode(p+c,add_special_tokens=False).ids for c in 'AB'];assert all(x[:-1]==a for x in b);assert [x[-1] for x in b]==choice.tolist();return a,[x[-1] for x in b]
allE={k:{(i,sw):encode(i,sw,k) for i in tr+va+te for sw in [False,True]} for k in questions}
def fresh():return AutoModelForCausalLM.from_pretrained(str(base),local_files_only=True,dtype=torch.float32)
def logits(m,ii,ks):
 seq=[allE[k][i,sw][0] for k in ks for i in ii for sw in [False,True]]
 lens=torch.tensor([len(v) for v in seq]);xx=torch.zeros((len(seq),int(lens.max())),dtype=torch.long);mask=torch.zeros_like(xx)
 for j,v in enumerate(seq):xx[j,:len(v)]=torch.tensor(v);mask[j,:len(v)]=1
 pos,inv=torch.unique(lens-1,sorted=True,return_inverse=True);v=m(input_ids=xx,attention_mask=mask,use_cache=False,logits_to_keep=pos).logits[torch.arange(len(seq)),inv,:][:,choice].float()
 d=(v[:,1]-v[:,0]).reshape(len(ks),len(ii),2);return torch.stack([d[:,:,0],-d[:,:,1]],-1)
def assess(m):
 global E
 V=[];T=[];gaps=[]
 for k in test_keys:
  E=allE[k];v=infer(m,va);t=infer(m,te);V.append(v.mean(1));T.append(t.mean(1));gaps.append(float((t[:,0]-t[:,1]).abs().mean()))
 v=torch.stack(V);t=torch.stack(T);cp,c=calibrate(v[0],t[0]);cal=(c['scale']*torch.logit(t.clamp(1e-7,1-1e-7))+c['bias']).sigmoid()
 return {'metrics':{k:metrics(cal[j],yy) for j,k in enumerate(test_keys)},'predictions':cal.tolist(),'raw_predictions':t.tolist(),'raw_range':float((t.max(0).values-t.min(0).values).mean()),'order_gaps':dict(zip(test_keys,gaps)),'calibration':c}
m=fresh();results={'base':assess(m)};del m;gc.collect()
prior=torch.full_like(yy,float(yv.mean()));results['prior']={'metrics':{'canonical':metrics(prior,yy)},'predictions':[prior.tolist()]}
for seed in [42,43]:
 for name in ['augmentation','joint']:
  torch.manual_seed(seed);m=get_peft_model(fresh(),LoraConfig(r=4,lora_alpha=8,target_modules=['q_proj','v_proj'],lora_dropout=0,task_type='CAUSAL_LM'));opt=torch.optim.AdamW([p for p in m.parameters() if p.requires_grad],lr=3e-4,weight_decay=0)
  order=list(tr);random.Random(seed).shuffle(order);losses=[]
  for step in range(4):
   m.train();ii=order[step*8:step*8+8];d=logits(m,ii,train_keys);label=torch.tensor([y(i) for i in ii],dtype=torch.float32)[None,:,None].expand_as(d)
   p=d.sigmoid();pm=p.mean(2);predloss=F.binary_cross_entropy_with_logits(d,label,pos_weight=torch.tensor(float((len(tr)-yt.sum())/yt.sum())));orderloss=(p[:,:,0]-p[:,:,1]).square().mean();semloss=(pm-pm.mean(0,keepdim=True)).square().mean()
   loss=predloss+(5*orderloss+5*semloss if name=='joint' else 0)
   opt.zero_grad();loss.backward();opt.step();losses.append([float(x.detach()) for x in [loss,predloss,orderloss,semloss]])
  key=f'{name}_{seed}';m.save_pretrained(out/key);a=assess(m);a['losses']=losses;a['adapter_sha']=sha(out/key/'adapter_model.safetensors');results[key]=a;del m,opt;gc.collect()
  m=PeftModel.from_pretrained(fresh(),str(out/key),local_files_only=True);re=assess(m);a['reload_delta']=max(abs(x-y) for v,w in zip(a['predictions'],re['predictions']) for x,y in zip(v,w));assert a['reload_delta']<1e-6;del m;gc.collect()
  print('RESULT',key,[round(a['metrics'][k]['auc'],6) for k in test_keys],a['raw_range'],a['order_gaps'],a['reload_delta'],flush=True);(out/'partial.json').write_text(json.dumps(results,indent=2))
r={'scope':'matched four-step weighted binary SFT on 3 templates, 2 seeds; augmentation vs joint order and semantic MSE; no isolation of individual regularizers; manually authored questions','questions':questions,'train_keys':train_keys,'test_keys':test_keys,'train_n':len(tr),'train_positive':int(yt.sum()),'cal_n':len(va),'cal_positive':int(yv.sum()),'test_n':len(te),'test_positive':int(yy.sum()),'test_indices':te,'test_labels':yy.tolist(),'results':results,'duration_s':time.time()-start}
(out/'receipt.json').write_text(json.dumps(r,indent=2,ensure_ascii=False));print('DONE',r['duration_s'],flush=True)

