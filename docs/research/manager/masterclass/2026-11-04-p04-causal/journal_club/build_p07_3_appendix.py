"""Append six evidence-scoped English slides with Japanese notes; retain 34-slide talk."""
from pathlib import Path
import io,re,json,hashlib
from pptx import Presentation
from pypdf import PdfReader,PdfWriter
from build_p04_45_appendix import base,card,text,TEAL,BLUE,ORANGE
from export_p04_45_pdf import render_slide
import export_p04_45_pdf as renderer
_original_wrap = renderer.wrap
def english_word_wrap(draw, value, font, width):
 lines=[]
 for source in value.split('\n'):
  if not source.strip(): lines.append(''); continue
  if ' ' not in source: lines.extend(_original_wrap(draw,source,font,width)); continue
  line=''
  for word in source.split():
   candidate=(line+' '+word).strip()
   if line and draw.textbbox((0,0),candidate,font=font)[2] > width:
    lines.append(line); line=word
   else: line=candidate
  if line: lines.append(line)
 return lines
renderer.wrap=english_word_wrap
from build_60min_journal_club import add_pdf_footer
ROOT=Path(__file__).resolve().parent
SLIDES=[
('COM-B: change conditions before adding persuasion','Six domains organize hypotheses; they do not diagnose a person.',
 [('Capability','Physical skills and ability\nPsychological skills, knowledge and attention'),('Opportunity','Physical time, tools and access\nSocial roles, support and norms'),('Motivation','Reflective goals and plans\nAutomatic feelings and learned responses')],
 'COM-Bは能力、機会、動機が相互に行動へ関わる枠組みである。各領域はさらに身体的・心理的、物理的・社会的、熟慮的・自動的に分かれる。未実行を意欲不足と決めつけない。疲労などを一つの領域へ機械的に分類せず、対象行動と状況を明確にする。図の候補は設計例であり実証済みの個人効果ではない。',
 'Michie et al. (2011), doi:10.1186/1748-5908-6-42'),
('From a barrier hypothesis to an authorized action','COM-B / Behaviour Change Wheel / BCT / BCIO have different jobs.',
 [('Specify the ingredient','BCT 1.4: action planning\nBCIO:007010\nA label is not efficacy evidence.'),('Check the candidate','Acceptability, practicability, effectiveness, affordability, spillovers and equity.'),('Reuse execution boundaries','Existing Grant / AuthorityVerifier\nOutbox + reconcile + verify\nInclude NO_ACTION.')],
 'COM-Bは障壁の仮説、BCWは介入機能、BCTは具体的内容、BCIOは機械可読な記述基盤である。計画を記録しただけで目標設定まで実施したと判定しない。APEASEで候補を検討するが、本人が拒否した行為や無権限の変更は便益と相殺して採用しない。既存のManager権限・照合・監査を再利用し、新しい並行実行基盤は作らない。',
 'BCTTv1 (2013); bciosearch.org/BCIO_007010; UCL APEASE'),
('Official GLM-HMM fitting was rerun for 93 people','55,800 existing human trials; scientific Step 7 cells unchanged.',
 [('Verified provenance','Official OSF files + SHA256\nSeed 0; pinned ssm fork\nAll 93 fits completed.'),('Close numerical agreement','Max transition difference:\n0.00000185\nMax over all parameters:\n0.00635'),('Not a whole-paper replication','Raw preprocessing, 100-mask model comparison and HDDM remain open.\nNo human intervention.')],
 '公式OSFのノートブックと処理済みデータを取得し、93人×600試行の2状態モデルを再学習した。著者の公開遷移確率との最大差は約0.00000185、全パラメータでは約0.00635だった。ビット単位の完全一致ではない。4人分は反復上限に達し、無反応368試行は元の符号化を保持した。全論文の再現、オンライン予測、反すう低減まで完了したと説明しない。',
 'Zhang & Kool (2026); evidence/P07-2_ZHANG_KOOL_STEP7_RESULTS.json'),
('The aggregation rule changes the duration claim','Retrospective state reconstruction is also not online forecasting.',
 [('Invert the mean transition','1 / (1 - mean(p_stay))\nON 24.94 / OFF 20.12 trials'),('Do not average blindly','mean(1 / (1 - p_stay)) differs.\nNear-one estimates are unstable.\nOnly 600 trials per person.'),('Separate information sets','Smoothing uses responses through T.\nFiltering uses responses through t.\nOnline validation remains open.')],
 '25/20試行は平均自己遷移確率を変換した集約値であり、各人の期待滞在長の平均でも直接観測した平均エピソード長でもない。1に極めて近い個人推定が大きな外挿を生むため、数百万試行を観測したとは言わない。また著者コードの平滑化は後続反応を使用する。オンライン推定は時刻tまでの情報で評価する必要がある。欠測処理や複数初期値の感度分析も未完である。',
 'Actual Step 7 rerun and authors parameter table; no causal-effect claim'),
('An independent RNT trial is a draft, not a result','The first proposed comparison tests the whole support package.',
 [('Proposed comparison','Frozen self-care support vs attention-matched general information.\n4 weeks; follow-up at week 8.'),('Measurement and planning','Appropriate-language PTQ.\nJapanese RTQ is not PTQ.\nAssumed d=.35 gives 326 total.'),('Not yet established','Independent team, ethics review, funding, registration and recruitment.\nNo participants or outcomes.')],
 '今回作成したのは内部の試験計画・統計解析計画の草案で、実試験は行っていない。支援パッケージ全体を比較するためAI個別化のみの効果は分離できない。PTQの適切な言語版を用い、日本語RTQを同じ尺度として扱わない。326人はd0.35、両側5%、検出力80%、脱落20%という仮定から解析人数を先に切り上げた設計値で、実測効果ではない。独立した責任者と安全対応をAIの自称で代用しない。',
 'Internal protocol v0.1; PTQ validation; SPIRIT 2025'),
('Prediction, execution and benefit need separate evidence','Next lesson: P07-4 / CBT, ACT and psychological flexibility.',
 [('Understand','Specify the action and context.\nPreserve multiple barrier hypotheses.'),('Act precisely','Reuse established techniques.\nRespect authority and withdrawal.\nNo action can be appropriate.'),('Measure what matters','Chosen behavior, burden and harms.\nIndependent comparison for benefit.\nDo not substitute app engagement.')],
 'P07-3の結論は、説得する言葉を増やすより、本人が望む行動を可能にする条件を調べることである。予測器の再現、実行レシート、介入による改善は別の証拠を必要とする。本人の目標変更や撤回を正当な選択として扱い、負担や害も測る。P07-3の教材は作成済みだが、実人間の反すう低減は未検証のまま。次の講義はP07-4である。',
 'P07-3 synthesis; canonical roadmap and specification')]

def make(prs,item):
 title,sub,cards,note,ref=item
 s=base(prs,'APPENDIX / P07-3 | BEHAVIOR CHANGE',title,sub,ref)
 for i,(head,body) in enumerate(cards):card(s,.62+4.23*i,2.35,3.98,3.70,head,body,[TEAL,BLUE,ORANGE][i],15.5)
 s.notes_slide.notes_text_frame.text=title+'\n\n'+note+'\n\n出典・範囲：'+ref
 return s

def numbered(prs,total):
 for i,sl in enumerate(prs.slides,1):
  for sh in sl.shapes:
   if getattr(sh,'has_text_frame',False) and re.fullmatch(r'\s*\d+\s*/\s*\d+\s*',sh.text):
    if sh.text_frame.paragraphs[0].runs:sh.text_frame.paragraphs[0].runs[0].text=f'{i} / {total}'
    else:sh.text=f'{i} / {total}'

def page_from_slide(slide):
 b=io.BytesIO();render_slide(slide).save(b,format='PDF',resolution=180.0);b.seek(0);return PdfReader(b).pages[0]

archive=ROOT/'AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx';pdf=ROOT/'AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf'
prs=Presentation(archive);assert len(prs.slides)==100,'Run only against the 100-slide baseline'
reader=PdfReader(pdf);assert len(reader.pages)==100
before=[s._element.xml for s in prs.slides]
for item in SLIDES:make(prs,item)
numbered(prs,106);prs.save(archive)
w=PdfWriter()
for p in reader.pages:w.add_page(p)
for sl in list(prs.slides)[100:]:w.add_page(page_from_slide(sl))
for i,p in enumerate(w.pages,1):add_pdf_footer(w,p,i,106)
with pdf.open('wb') as f:w.write(f)
notes='# Research archive: 106 slides / 日本語ノート\n\n'
for i,s in enumerate(prs.slides,1):notes+=f'## {i:02d}\n\n'+s.notes_slide.notes_text_frame.text+'\n\n'
(ROOT/'SPEAKER_NOTES_JA.md').write_text(notes)
public=ROOT/'AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pptx';publicpdf=ROOT/'AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pdf'
p=Presentation(public);assert len(p.slides)==34
# Replace only slides 31 and 34 with concise current evidence and architecture.
selected={30:SLIDES[1],33:SLIDES[5]}
for index,item in selected.items():
 sl=p.slides[index]
 for sh in list(sl.shapes):sh._element.getparent().remove(sh._element)
 temp=Presentation();temp.slide_width=p.slide_width;temp.slide_height=p.slide_height
 made=make(temp,item)
 from copy import deepcopy
 for sh in made.shapes:
  if not sh.is_placeholder:
   assert sh.left is not None and sh.top is not None
   sl.shapes._spTree.insert_element_before(deepcopy(sh._element),'p:extLst')
 sl.notes_slide.notes_text_frame.text=made.notes_slide.notes_text_frame.text
 if index==33:sl.notes_slide.notes_text_frame.text+='\n\n更新：公式Step7の93人再学習は完了。4人の反復上限、無反応368試行、平滑化とオンライン推定の差を明記。独立RNT試験は内部草案で未実施。'
numbered(p,34);p.save(public)
r=PdfReader(publicpdf);assert len(r.pages)==34;out=PdfWriter()
for i,page in enumerate(r.pages):out.add_page(page_from_slide(p.slides[i]) if i in selected else page)
for i,page in enumerate(out.pages,1):
 if i-1 in selected:add_pdf_footer(out,page,i,34)
with publicpdf.open('wb') as f:out.write(f)
script=ROOT/'SPEAKER_SCRIPT_60MIN_JA.md';s=script.read_text();s+='\n\n## 2026-11-06 更新：31枚目と34枚目の差し替え原稿\n\n'
for i in selected:s+=f'### {i+1}枚目\n\n'+p.slides[i].notes_slide.notes_text_frame.text+'\n\n'
script.write_text(s)
# Actual shape/notes/count assertions, not an efficacy check.
assert len(Presentation(archive).slides)==106 and len(PdfReader(pdf).pages)==106
assert len(Presentation(public).slides)==34 and len(PdfReader(publicpdf).pages)==34
assert all(s.notes_slide.notes_text_frame.text.strip() for s in prs.slides)
receipt={'archive_slides':106,'archive_pdf_pages':106,'public_slides':34,'public_pdf_pages':34,'public_changed_slides':[31,34],'new_archive_slides':[101,102,103,104,105,106],'new_slide_body_language':'English','speaker_notes_language':'Japanese','historical_body_language':'unchanged; many earlier slides remain Japanese','pdf_method':'preserve existing pages; render changed/new native PPTX shapes with existing repository helper','artifacts':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in [archive,pdf,public,publicpdf]}}
(ROOT/'P07-3_SLIDE_SYNC_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
for i in [100,101,102,103,104,105]:render_slide(prs.slides[i]).save(ROOT/f'P07-3_CHECK_{i+1}.png')
print(json.dumps(receipt,indent=2))
