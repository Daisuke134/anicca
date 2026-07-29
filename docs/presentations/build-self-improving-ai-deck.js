const fs = require("fs");
const os = require("os");
const path = require("path");
const pptxgen = require("pptxgenjs");
const html2pptx = require("/Users/anicca/anicca-project/.claude/skills/pptx/scripts/html2pptx.js");

const OUT = path.join(__dirname, "life-manager-builds-life-manager.pptx");
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), "lm-self-builder-deck-"));

const C = {
  bg: "#11161C",
  panel: "#1B232D",
  panel2: "#242E3A",
  text: "#F4F7FA",
  muted: "#9EADBA",
  cyan: "#44D7E8",
  amber: "#F4B942",
  violet: "#A98BFF",
  green: "#4DDB91",
  coral: "#FF6B6B",
};

const css = `
* { box-sizing: border-box; }
html { background: ${C.bg}; }
body {
  width: 720pt; height: 405pt; margin: 0; padding: 0;
  background: ${C.bg}; color: ${C.text}; font-family: Arial, sans-serif;
  display: flex; flex-direction: column; overflow: hidden;
}
.top { height: 62pt; margin: 0 34pt; display: flex; align-items: end; border-bottom: 1pt solid #33404D; }
.num { width: 42pt; }
.num p { margin: 0 0 12pt 0; color: ${C.cyan}; font-size: 11pt; font-weight: bold; }
.top h1 { margin: 0 0 10pt 0; font-size: 26pt; line-height: 1.05; color: ${C.text}; }
.content { flex: 1; margin: 22pt 34pt 20pt 34pt; display: flex; flex-direction: column; }
.footer { height: 22pt; margin: 0 34pt; display: flex; align-items: start; }
.footer p { margin: 0; color: #718191; font-size: 7pt; }
.hero { justify-content: center; }
.hero h1 { margin: 0; font-size: 49pt; line-height: 0.98; letter-spacing: -1.5pt; }
.hero .sub { margin: 16pt 0 0 0; font-size: 18pt; color: ${C.muted}; }
.hero .kicker { margin: 0 0 12pt 0; color: ${C.cyan}; font-size: 11pt; font-weight: bold; letter-spacing: 2pt; }
.row { display: flex; gap: 12pt; width: 100%; }
.col { flex: 1; display: flex; flex-direction: column; gap: 10pt; }
.card { flex: 1; background: ${C.panel}; border-radius: 8pt; padding: 14pt; border: 1pt solid #2C3946; }
.card h2 { margin: 0 0 7pt 0; font-size: 16pt; }
.card p { margin: 0; font-size: 12pt; line-height: 1.25; color: ${C.muted}; }
.big { font-size: 28pt !important; line-height: 1.1 !important; font-weight: bold; color: ${C.text} !important; }
.huge { font-size: 38pt !important; line-height: 1.05 !important; font-weight: bold; color: ${C.text} !important; }
.cyan { color: ${C.cyan} !important; }
.amber { color: ${C.amber} !important; }
.violet { color: ${C.violet} !important; }
.green { color: ${C.green} !important; }
.coral { color: ${C.coral} !important; }
.muted { color: ${C.muted} !important; }
.mono { font-family: "Courier New", monospace; }
.code { background: #0C1116; border: 1pt solid #2B3743; border-radius: 8pt; padding: 15pt; }
.code p { margin: 0 0 6pt 0; font-family: "Courier New", monospace; font-size: 13pt; line-height: 1.15; }
.center { text-align: center; }
.flow { display: flex; align-items: center; justify-content: center; gap: 6pt; width: 100%; }
.node { min-width: 77pt; background: ${C.panel}; border-radius: 7pt; padding: 10pt 8pt; border: 2pt solid ${C.cyan}; }
.node p { margin: 0; text-align: center; font-size: 10.5pt; font-weight: bold; }
.arrow { margin: 0; color: ${C.muted}; font-size: 18pt; font-weight: bold; }
.pill { border-radius: 99pt; padding: 6pt 10pt; background: ${C.panel2}; }
.pill p { margin: 0; font-size: 9pt; font-weight: bold; }
.statement { margin: 0; font-size: 30pt; line-height: 1.12; font-weight: bold; }
.caption { margin: 10pt 0 0 0; font-size: 13pt; color: ${C.muted}; }
.grid2 { display: flex; flex-wrap: wrap; gap: 10pt; }
.grid2 .card { flex: 0 0 calc(50% - 5pt); }
.grid3 { display: flex; flex-wrap: wrap; gap: 8pt; }
.grid3 .card { flex: 0 0 calc(33.333% - 6pt); padding: 10pt; }
.grid3 .card h2 { font-size: 13pt; }
.grid3 .card p { font-size: 10pt; }
.table { width: 100%; display: flex; flex-direction: column; border: 1pt solid #33404D; border-radius: 7pt; overflow: hidden; }
.tr { display: flex; min-height: 34pt; border-bottom: 1pt solid #33404D; }
.tr:last-child { border-bottom: 0; }
.th { background: ${C.panel2}; }
.cell { flex: 1; padding: 8pt 10pt; border-right: 1pt solid #33404D; }
.cell:last-child { border-right: 0; }
.cell p { margin: 0; font-size: 10.5pt; line-height: 1.18; }
.th .cell p { font-weight: bold; color: ${C.text}; }
.source { margin-top: auto; padding-top: 7pt; border-top: 1pt solid #2B3743; }
.source p { margin: 0; font-size: 7.5pt; color: #80909F; }
.lane { padding: 12pt; background: ${C.panel}; border-radius: 8pt; }
.lane h2 { margin: 0 0 9pt 0; font-size: 13pt; letter-spacing: 1pt; }
.lane p { margin: 0; font-size: 11pt; line-height: 1.25; }
.divider { height: 1pt; background: #3A4857; margin: 10pt 0; }
.quote { padding-left: 15pt; border-left: 7pt solid ${C.cyan}; }
.quote p { margin: 0; font-size: 25pt; line-height: 1.15; font-weight: bold; }
`;

const slides = [
  {
    title: "",
    body: `<div class="content hero">
      <p class="kicker">SELF-IMPROVING SOFTWARE</p>
      <h1>Life Manager<br><span class="cyan">Builds Life Manager</span></h1>
      <p class="sub">AIが自分の失敗を観測し、Evalを作り、自分を修正するまで</p>
      <div class="flow" style="justify-content:flex-start; margin-top:24pt;">
        <div class="pill"><p class="cyan">OBSERVABILITY</p></div><p class="arrow">→</p>
        <div class="pill"><p class="amber">EVAL</p></div><p class="arrow">→</p>
        <div class="pill"><p class="violet">GRAPH</p></div><p class="arrow">→</p>
        <div class="pill"><p class="green">LOOP</p></div>
      </div>
    </div>`,
    note: "一件の失敗だけを追いながら、Life Managerが自分を直すsystemを説明する。",
  },
  {
    title: "午前7時、電話は鳴らなかった",
    body: `<div class="content">
      <div class="row" style="height:205pt;">
        <div class="card"><h2 class="green">INTERNAL STATE</h2><p class="huge">DONE</p><p>Scheduler completed<br>Agent: “wake call sent”</p></div>
        <div class="card" style="border-color:${C.coral};"><h2 class="coral">REAL WORLD</h2><p class="huge coral">SILENT</p><p>Provider timeout<br>User received no call</p></div>
      </div>
      <p class="statement center" style="margin-top:18pt;">System activity <span class="coral">≠</span> real-world effect</p>
    </div>`,
    note: "外部効果のreceiptがなければ、Agentは成功を誤認する。",
  },
  {
    title: "自己編集は自己改善ではない",
    body: `<div class="content">
      <div class="code">
        <p><span class="muted">code changed</span>                    = self-editing</p>
        <p><span class="muted">task completed</span>                  = autonomy</p>
        <p><span class="green">candidate beats baseline safely</span> = self-improvement</p>
      </div>
      <div class="quote" style="margin-top:25pt;"><p>変更ではなく、<span class="amber">改善の証拠</span>が必要。</p></div>
    </div>`,
    note: "commit数やAgent稼働時間を改善metricにしない。",
  },
  {
    title: "四つは同じ身体の器官",
    body: `<div class="content"><div class="row" style="height:238pt;">
      <div class="card" style="border-color:${C.cyan};"><h2 class="cyan">OBSERVABILITY</h2><p class="big">感じる</p><p>何が起きたか</p></div>
      <div class="card" style="border-color:${C.amber};"><h2 class="amber">EVAL</h2><p class="big">採点する</p><p>直ったか</p></div>
      <div class="card" style="border-color:${C.violet};"><h2 class="violet">GRAPH</h2><p class="big">分岐する</p><p>次に何をするか</p></div>
      <div class="card" style="border-color:${C.green};"><h2 class="green">LOOP</h2><p class="big">継続する</p><p>どう学び続けるか</p></div>
    </div></div>`,
    note: "Observability、Eval、Graph、Loopを別々の流行語として扱わない。",
  },
  {
    title: "Observabilityは感覚器",
    body: `<div class="content">
      <div class="flow" style="margin-top:14pt;">
        <div class="node"><p>schedule<br>claim</p></div><p class="arrow">→</p>
        <div class="node"><p>context<br>load</p></div><p class="arrow">→</p>
        <div class="node"><p>provider<br>call</p></div><p class="arrow">→</p>
        <div class="node" style="border-color:${C.coral};"><p class="coral">effect<br>verify</p></div><p class="arrow">→</p>
        <div class="node"><p>outcome<br>observe</p></div>
      </div>
      <div class="row" style="margin-top:28pt;">
        <div class="pill"><p>LOG</p></div><div class="pill"><p>METRIC</p></div>
        <div class="pill"><p>TRACE</p></div><div class="pill"><p>EFFECT RECEIPT</p></div>
      </div>
      <div class="source"><p>OpenTelemetry: “telemetry is also used as a feedback loop”</p></div>
    </div>`,
    note: "OpenTelemetryでrunを同じtrace_idにつなぎ、receiptまで観測する。",
  },
  {
    title: "何千人分をどう観測するか",
    body: `<div class="content">
      <div class="table">
        <div class="tr th"><div class="cell"><p class="green">全run</p></div><div class="cell"><p class="amber">深く保持</p></div><div class="cell"><p class="coral">原則出さない</p></div></div>
        <div class="tr"><div class="cell"><p>error / latency / cost</p></div><div class="cell"><p>failures / safety</p></div><div class="cell"><p>raw prompt</p></div></div>
        <div class="tr"><div class="cell"><p>version / receipt</p></div><div class="cell"><p>redacted exemplar</p></div><div class="cell"><p>health / location</p></div></div>
        <div class="tr"><div class="cell"><p>state transition</p></div><div class="cell"><p>bounded debug</p></div><div class="cell"><p>calendar / Telegram</p></div></div>
      </div>
      <p class="statement center" style="margin-top:22pt;">Aggregate everyone. <span class="cyan">Read nobody by default.</span></p>
    </div>`,
    note: "全runの軽量system evidenceと、少数のredacted failure traceを分ける。",
  },
  {
    title: "Automated Eval Engineeringは試験工場",
    body: `<div class="content">
      <div class="flow" style="margin-top:12pt;">
        <div class="node" style="border-color:${C.coral};"><p>TRACE</p></div><p class="arrow">→</p>
        <div class="node"><p>REDACT</p></div><p class="arrow">→</p>
        <div class="node" style="border-color:${C.amber};"><p>FIXTURE</p></div><p class="arrow">→</p>
        <div class="node" style="border-color:${C.coral};"><p>BASELINE<br>FAIL</p></div><p class="arrow">→</p>
        <div class="node" style="border-color:${C.amber};"><p>SEALED<br>EVAL</p></div>
      </div>
      <p class="statement center" style="margin-top:34pt;">Production failure becomes a<br><span class="amber">falsifiable contract.</span></p>
      <div class="source"><p>LangChain: “mine traces -> identify a failure -> build an eval”</p></div>
    </div>`,
    note: "production failureを再実行可能な採点契約へ変える。",
  },
  {
    title: "一つの点数では昇格しない",
    body: `<div class="content"><div class="grid3">
      <div class="card"><h2>1 · Reproduction</h2><p>同じfailureか</p></div>
      <div class="card"><h2>2 · Unit / Integration</h2><p>局所contract</p></div>
      <div class="card"><h2>3 · Real E2E</h2><p>外部効果</p></div>
      <div class="card"><h2>4 · Sealed holdout</h2><p>過適合防止</p></div>
      <div class="card"><h2>5 · Security / Policy</h2><p>境界違反</p></div>
      <div class="card"><h2>6 · Cost / Latency</h2><p>資源退化</p></div>
      <div class="card" style="border-color:${C.green};"><h2 class="green">7 · Canary outcome</h2><p>ユーザー価値</p></div>
    </div></div>`,
    note: "MakerとCheckerを分離し、LLM judgeを唯一のgateにしない。",
  },
  {
    title: "Graph Engineeringは状態と証拠",
    body: `<div class="content">
      <div class="code">
        <p>OBSERVED → CLUSTERED → REPRODUCED → EVAL_READY</p>
        <p>→ IMPLEMENTED → VERIFIED → CANARY → <span class="green">MEASURED</span></p>
      </div>
      <div class="row" style="margin-top:18pt;">
        <div class="pill"><p class="coral">RETRY_WAIT</p></div>
        <div class="pill"><p class="coral">QUARANTINED</p></div>
        <div class="pill"><p class="coral">ROLLED_BACK</p></div>
        <div class="pill"><p class="coral">CIRCUIT_OPEN</p></div>
      </div>
      <p class="caption center">Makerの “done” では進まない。SHAとreceiptで進む。</p>
      <div class="source"><p>LangChain: “loops are simple graphs”</p></div>
    </div>`,
    note: "Graphはstate、transition receipt、failure pathを定義する。",
  },
  {
    title: "Loop Engineeringはpromptする人を置き換える",
    body: `<div class="content">
      <div class="flow" style="flex-wrap:wrap; margin-top:8pt;">
        <div class="node"><p>OBSERVE</p></div><p class="arrow">→</p>
        <div class="node"><p>DIAGNOSE</p></div><p class="arrow">→</p>
        <div class="node" style="border-color:${C.amber};"><p>EVALUATE</p></div><p class="arrow">→</p>
        <div class="node"><p>CHANGE</p></div>
      </div>
      <div class="flow" style="margin-top:12pt;">
        <div class="node"><p>VERIFY</p></div><p class="arrow">→</p>
        <div class="node"><p>PROMOTE<br>/ ROLLBACK</p></div><p class="arrow">→</p>
        <div class="node" style="border-color:${C.green};"><p>MEASURE</p></div><p class="arrow">→</p>
        <div class="node" style="border-color:${C.green};"><p>LEARN</p></div>
      </div>
      <p class="statement center" style="margin-top:20pt;">The loop closes at <span class="green">outcome</span>, not at merge.</p>
      <div class="source"><p>Addy Osmani: “replacing yourself as the person who prompts the agent”</p></div>
    </div>`,
    note: "実metricとlearning receiptまで戻ってloopが閉じる。",
  },
  {
    title: "内側で観測し、外側で修正する",
    body: `<div class="content">
      <div class="lane" style="border-left:7pt solid ${C.cyan};"><h2 class="cyan">PRODUCT PLANE · LIFE MANAGER</h2><p>wake · travel · ask · writer · API → trace / metric / effect receipt</p></div>
      <p class="arrow center" style="margin:7pt 0;">↓ redacted, append-only</p>
      <div class="lane" style="border-left:7pt solid ${C.violet};"><h2 class="violet">SELF-BUILDER CONTROL PLANE</h2><p>Collector → Eval Builder → Maker → Checker → Promoter → Outcome Auditor</p></div>
      <p class="caption center">Product has no merge credential. Maker has no production secret.</p>
    </div>`,
    note: "Product PlaneとSelf-Builderのcredentialとprocessを分離する。",
  },
  {
    title: "採用tool stack",
    body: `<div class="content"><div class="grid3">
      <div class="card"><h2 class="cyan">OpenTelemetry</h2><p>Telemetry standard</p></div>
      <div class="card"><h2 class="cyan">Langfuse</h2><p>Trace / Eval UI</p></div>
      <div class="card"><h2 class="violet">Inngest</h2><p>Durable Graph</p></div>
      <div class="card"><h2 class="violet">Postgres</h2><p>Authority / Audit</p></div>
      <div class="card"><h2 class="amber">GitHub</h2><p>Issue / PR / Gates</p></div>
      <div class="card"><h2 class="green">Mixpanel + Sentry</h2><p>Outcome / Error</p></div>
      <div class="card"><h2>Codex Terra / Sol</h2><p>Workers</p></div>
    </div></div>`,
    note: "toolを増やすのではなく、一役一toolで既存資産を再利用する。",
  },
  {
    title: "現在あるもの",
    body: `<div class="content"><div class="grid2">
      <div class="card" style="border-color:${C.green};"><h2 class="green">6 Inngest functions</h2><p>durable product graph</p></div>
      <div class="card" style="border-color:${C.green};"><h2 class="green">Tenant isolation</h2><p>one failure does not stop all</p></div>
      <div class="card" style="border-color:${C.green};"><h2 class="green">Node eval / tests</h2><p>deterministic contracts</p></div>
      <div class="card" style="border-color:${C.green};"><h2 class="green">Receipts / signals</h2><p>provider and product evidence</p></div>
      <div class="card" style="border-color:${C.green};"><h2 class="green">GitHub gates</h2><p>Actions + protected branch</p></div>
      <div class="card" style="border-color:${C.green};"><h2 class="green">Holdout / revert</h2><p>Writer patterns</p></div>
    </div></div>`,
    note: "ここまではexisting codeで確認できる現在地。",
  },
  {
    title: "まだないもの",
    body: `<div class="content"><div class="grid2">
      <div class="card" style="border-style:dashed; border-color:${C.amber};"><h2 class="amber">Common OTel envelope</h2><p>target</p></div>
      <div class="card" style="border-style:dashed; border-color:${C.amber};"><h2 class="amber">Failure cluster store</h2><p>target</p></div>
      <div class="card" style="border-style:dashed; border-color:${C.amber};"><h2 class="amber">Automated Eval factory</h2><p>target</p></div>
      <div class="card" style="border-style:dashed; border-color:${C.amber};"><h2 class="amber">Evidence Issue projector</h2><p>target</p></div>
      <div class="card" style="border-style:dashed; border-color:${C.amber};"><h2 class="amber">Maker / Checker</h2><p>target dispatcher</p></div>
      <div class="card" style="border-style:dashed; border-color:${C.amber};"><h2 class="amber">Canary → outcome lineage</h2><p>target</p></div>
    </div><p class="caption center coral">Productionで自己mergeするclosed loopは、まだ完成していない。</p></div>`,
    note: "architecture targetとproduction current stateを混ぜない。",
  },
  {
    title: "最初のvertical slice",
    body: `<div class="content">
      <div class="flow" style="margin-top:10pt;">
        <div class="node" style="border-color:${C.coral};"><p>TIMEOUT</p></div><p class="arrow">→</p>
        <div class="node"><p>TRACE</p></div><p class="arrow">→</p>
        <div class="node"><p>CLUSTER</p></div><p class="arrow">→</p>
        <div class="node" style="border-color:${C.amber};"><p>FAILING<br>EVAL</p></div>
      </div>
      <div class="flow" style="margin-top:13pt;">
        <div class="node"><p>ISSUE</p></div><p class="arrow">→</p>
        <div class="node"><p>ISOLATED<br>PR</p></div><p class="arrow">→</p>
        <div class="node"><p>CHECKER</p></div><p class="arrow">→</p>
        <div class="node" style="border-color:${C.green};"><p>LEARNING<br>RECEIPT</p></div>
      </div>
      <p class="statement center" style="margin-top:18pt;">One failure. <span class="green">Complete lineage.</span></p>
    </div>`,
    note: "最初から全sourceをつながず、一件をE2Eで閉じる。",
  },
  {
    title: "自動mergeは契約",
    body: `<div class="content"><div class="row">
      <div class="code" style="flex:1.35;">
        <p>allowlisted_low_risk: <span class="green">true</span></p>
        <p>baseline: <span class="coral">fail</span></p>
        <p>candidate: <span class="green">pass</span></p>
        <p>sealed_holdout_delta: <span class="green">">= 0"</span></p>
        <p>security_regression: <span class="green">false</span></p>
        <p>sensitive_path: <span class="green">false</span></p>
        <p>rollback_ready: <span class="green">true</span></p>
      </div>
      <div class="col">
        <div class="card" style="border-color:${C.green};"><h2 class="green">ALL TRUE</h2><p class="big">MERGE</p></div>
        <div class="card" style="border-color:${C.coral};"><h2 class="coral">ELSE</h2><p class="big coral">QUARANTINE</p></div>
      </div>
    </div></div>`,
    note: "自動mergeはLLMの自信ではなくmachine-readable policyで決める。",
  },
  {
    title: "No Human Loopの境界",
    body: `<div class="content">
      <div class="quote"><p>Remove humans from <span class="green">execution</span>.<br>Encode humans into <span class="amber">goals, evidence, permissions, rollback.</span></p></div>
      <div class="row" style="margin-top:23pt;">
        <div class="card"><h2 class="green">MUTABLE</h2><p>prompt · tool · local code<br>routing · retry · worker config</p></div>
        <div class="card" style="border-color:${C.amber};"><h2 class="amber">IMMUTABLE</h2><p>goal · policy · secret<br>sealed holdout · promoter · audit</p></div>
      </div>
    </div>`,
    note: "No-Human-Loopはbounded human-free executionであり、governance消去ではない。",
  },
  {
    title: "",
    body: `<div class="content hero center">
      <p class="kicker">FINAL TAKEAWAY</p>
      <h1 style="font-size:42pt;">Self-improving AI is not a model.</h1>
      <p class="statement" style="margin-top:16pt;">It is a loop that can <span class="green">prove</span> it got better.</p>
      <div class="flow" style="margin-top:31pt;">
        <div class="pill"><p class="cyan">OBSERVE HONESTLY</p></div>
        <div class="pill"><p class="amber">EVALUATE INDEPENDENTLY</p></div>
        <div class="pill"><p class="green">PROMOTE REVERSIBLY</p></div>
      </div>
    </div>`,
    note: "証拠、独立評価、可逆昇格をcodeにした時、Life Managerは自分をbuildし始める。",
  },
];

function page(slide, index) {
  const top = slide.title
    ? `<div class="top"><div class="num"><p>${String(index + 1).padStart(2, "0")}</p></div><h1>${slide.title}</h1></div>`
    : "";
  return `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body>
    ${top}${slide.body}<div class="footer"><p>LIFE MANAGER BUILDS LIFE MANAGER · ANICCA</p></div>
  </body></html>`;
}

async function main() {
  const pptx = new pptxgen();
  pptx.layout = "LAYOUT_16x9";
  pptx.author = "Anicca";
  pptx.subject = "Self-improving AI architecture";
  pptx.title = "Life Manager Builds Life Manager";
  pptx.company = "Anicca";
  pptx.lang = "ja-JP";
  pptx.theme = {
    headFontFace: "Arial",
    bodyFontFace: "Arial",
    lang: "ja-JP",
  };

  for (let i = 0; i < slides.length; i += 1) {
    const file = path.join(TMP, `slide-${String(i + 1).padStart(2, "0")}.html`);
    fs.writeFileSync(file, page(slides[i], i), "utf8");
    const { slide } = await html2pptx(file, pptx, { tmpDir: TMP });
    if (typeof slide.addNotes === "function") slide.addNotes(slides[i].note);
  }

  await pptx.writeFile({ fileName: OUT });
  console.log(OUT);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
