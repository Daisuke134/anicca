const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');
const html2pptx = require('../../../.claude/skills/pptx/scripts/html2pptx');

const ROOT = __dirname;
const HTML_DIR = path.join(ROOT, 'html');
const OUT = path.join(ROOT, 'life-manager-lt-ja-2026-07-28.pptx');

const C = {
  bg: '#081018',
  surface: '#111C27',
  surface2: '#182635',
  ink: '#F7F4EA',
  muted: '#A6B3BE',
  cyan: '#57D6C7',
  amber: '#FFC857',
  coral: '#FF7A66',
  green: '#73D49C',
  purple: '#C89BFF',
  line: '#2A3A49',
};

const baseCss = `
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; width: 1280px; height: 720px; overflow: hidden; }
  body { font-family: Arial, sans-serif; background: ${C.bg}; color: ${C.ink}; }
  .slide { position: relative; width: 1280px; height: 720px; overflow: hidden; background: ${C.bg}; }
  h1,h2,h3,p { margin: 0; padding: 0; }
  h1 { font-size: 68px; line-height: 1.08; letter-spacing: -1.5px; font-weight: 700; }
  h2 { font-size: 48px; line-height: 1.14; letter-spacing: -0.8px; font-weight: 700; }
  h3 { font-size: 25px; line-height: 1.25; font-weight: 700; }
  p { font-size: 25px; line-height: 1.4; }
  .kicker { font-size: 16px; line-height: 1; letter-spacing: 3px; font-weight: 700; color: ${C.cyan}; }
  .muted { color: ${C.muted}; }
  .small { font-size: 24px; line-height: 1.4; }
  .tiny { font-size: 17px; line-height: 1.35; }
  .accent { color: ${C.cyan}; }
  .amber { color: ${C.amber}; }
  .coral { color: ${C.coral}; }
  .green { color: ${C.green}; }
  .purple { color: ${C.purple}; }
  .title { position: absolute; left: 72px; top: 58px; width: 1136px; }
  .title h2 { margin-top: 14px; }
  .rule { position: absolute; left: 72px; right: 72px; top: 148px; height: 2px; background: ${C.line}; }
  .footer { position: absolute; left: 72px; right: 72px; bottom: 28px; display: flex; justify-content: space-between; align-items: center; }
  .footer p { font-size: 13px; line-height: 1; letter-spacing: 1.2px; color: ${C.muted}; }
  .footer .num { color: ${C.cyan}; font-weight: 700; }
  .card { background: ${C.surface}; border: 1px solid ${C.line}; border-radius: 18px; padding: 24px; }
  .chip { display: inline-flex; align-items: center; border-radius: 999px; border: 1px solid ${C.line}; padding: 8px 13px; }
  .chip p { font-size: 14px; line-height: 1; font-weight: 700; }
  .status-live { border-color: ${C.green}; color: ${C.green}; }
  .status-next { border-color: ${C.amber}; color: ${C.amber}; }
  .status-vision { border-color: ${C.purple}; color: ${C.purple}; }
  .numCircle { width: 54px; height: 54px; border-radius: 50%; background: ${C.cyan}; display:flex; align-items:center; justify-content:center; }
  .numCircle p { color: ${C.bg}; font-size: 23px; line-height: 1; font-weight: 700; }
`;

function footer(n, label = 'LIFE MANAGER / LT') {
  return `<div class="footer"><p>${label}</p><p class="num">${String(n).padStart(2, '0')}</p></div>`;
}

function frame(n, inner, extraCss = '') {
  return `<!doctype html><html><head><meta charset="utf-8"><style>${baseCss}${extraCss}</style></head>
  <body><section class="slide">${inner}${footer(n)}</section></body></html>`;
}

const slides = [
  {
    note: '導入。今日は、Life Managerを「何を作っているか」「どこまでできたか」「何が残っているか」の順に話す。',
    html: frame(1, `
      <div style="position:absolute;left:72px;top:68px;width:720px;">
        <p class="kicker">LIFE MANAGER / LIGHTNING TALK</p>
        <h1 style="margin-top:28px;">理想の生活が<br><span class="accent">向こうから来る。</span></h1>
        <p class="muted" style="margin-top:28px;width:650px;">1人・1台のスマホから、財務・身体・精神を動かす生活OSをつくる</p>
      </div>
      <div style="position:absolute;right:82px;top:96px;width:320px;height:520px;">
        <div style="position:absolute;left:38px;top:0;width:244px;height:480px;border:3px solid ${C.ink};border-radius:42px;background:${C.surface};">
          <div style="position:absolute;left:74px;top:16px;width:96px;height:8px;border-radius:8px;background:${C.line};"></div>
          <div style="position:absolute;left:24px;top:72px;width:196px;">
            <p class="tiny muted">07:50  LIFE MANAGER</p>
            <div class="card" style="margin-top:12px;padding:18px;border-color:${C.cyan};">
              <p class="small" style="font-weight:700;">9:30 出発。</p>
              <p class="tiny muted" style="margin-top:8px;">雨なので10分早めました。</p>
            </div>
            <div class="card" style="margin-top:14px;padding:18px;">
              <p class="tiny muted">完了</p>
              <p class="small" style="margin-top:7px;">移動時間を追加</p>
            </div>
            <div class="card" style="margin-top:14px;padding:18px;">
              <p class="tiny muted">次</p>
              <p class="small" style="margin-top:7px;">T-10 電話</p>
            </div>
          </div>
          <div style="position:absolute;left:92px;bottom:14px;width:60px;height:5px;border-radius:5px;background:${C.muted};"></div>
        </div>
      </div>
    `),
  },
  {
    note: 'Life Managerが解く問題は、アプリ不足ではない。人間の頭が、予定・移動・連絡・健康・収入のオペレーターになっていること。',
    html: frame(2, `
      <div class="title"><p class="kicker">WHY</p><h2>問題は、生活が<span class="coral">人間の頭のRAM</span>を食べ続けること</h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:76px;top:205px;width:1128px;height:380px;">
        <div class="card" style="position:absolute;left:0;top:0;width:260px;height:150px;">
          <p class="tiny coral">SCHEDULE</p><h3 style="margin-top:12px;">次は何時？</h3><p class="small muted" style="margin-top:10px;">時計を見続ける</p>
        </div>
        <div class="card" style="position:absolute;right:0;top:0;width:260px;height:150px;">
          <p class="tiny amber">TRAVEL</p><h3 style="margin-top:12px;">何分前に出る？</h3><p class="small muted" style="margin-top:10px;">毎回逆算する</p>
        </div>
        <div class="card" style="position:absolute;left:0;bottom:0;width:260px;height:150px;">
          <p class="tiny purple">CARE</p><h3 style="margin-top:12px;">予約しなきゃ</h3><p class="small muted" style="margin-top:10px;">先送りが住みつく</p>
        </div>
        <div class="card" style="position:absolute;right:0;bottom:0;width:260px;height:150px;">
          <p class="tiny green">MONEY</p><h3 style="margin-top:12px;">もっと稼がなきゃ</h3><p class="small muted" style="margin-top:10px;">労働時間に縛られる</p>
        </div>
        <div style="position:absolute;left:404px;top:77px;width:320px;height:226px;border:2px solid ${C.cyan};border-radius:28px;background:${C.surface2};display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;">
          <p class="kicker">HUMAN RAM</p>
          <h2 style="font-size:55px;margin-top:18px;">常時満杯</h2>
          <p class="small muted" style="margin-top:12px;">忘れないために生きている</p>
        </div>
      </div>
    `),
  },
  {
    note: '北極星。Life Managerは三つの臓器を持つ。財務・身体・精神を別々のアプリで管理するのではなく、一つの文脈から動かす。',
    html: frame(3, `
      <div class="title"><p class="kicker">NORTH STAR</p><h2>Life Manager = <span class="accent">頭脳</span> + 3つの臓器</h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:72px;top:205px;width:1136px;display:flex;gap:22px;">
        <div class="card" style="width:364px;height:310px;border-top:6px solid ${C.green};">
          <p class="tiny green">PHYSICAL</p><h2 style="font-size:42px;margin-top:18px;">身体</h2>
          <p class="small muted" style="margin-top:22px;">未通院や未ケアを見つけ、生活圏と予定から予約する。</p>
          <p class="small" style="margin-top:26px;">「木曜18時、歯医者を取った」</p>
        </div>
        <div class="card" style="width:364px;height:310px;border-top:6px solid ${C.purple};">
          <p class="tiny purple">MENTAL</p><h2 style="font-size:42px;margin-top:18px;">精神</h2>
          <p class="small muted" style="margin-top:22px;">予定と場所から、効く瞬間に支援する。固定時刻ではない。</p>
          <p class="small" style="margin-top:26px;">「準備は全部入ってる」</p>
        </div>
        <div class="card" style="width:364px;height:310px;border-top:6px solid ${C.amber};">
          <p class="tiny amber">FINANCIAL</p><h2 style="font-size:42px;margin-top:18px;">財務</h2>
          <p class="small muted" style="margin-top:22px;">AIが自分のwalletで稼ぎ、自分の計算資源を払い、余剰を送る。</p>
          <p class="small" style="margin-top:26px;">「今月 $120 稼いだ」</p>
        </div>
      </div>
      <div style="position:absolute;left:310px;top:554px;width:660px;text-align:center;">
        <p class="small"><span class="accent">頭脳：</span> intent-aware context graph ─ その人にとって重要な未処理を選ぶ</p>
      </div>
    `),
  },
  {
    note: '制作方法そのものも実験。私はPCの前に座らず、ChatGPTのiPhoneアプリからMac mini上のCodexへ指示し、コード・テスト・デプロイまで進めている。',
    html: frame(4, `
      <div class="title"><p class="kicker">HOW I BUILD</p><h2>このシステムは、<span class="amber">スマホだけで指揮</span>してつくっている</h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:84px;top:230px;width:1112px;height:300px;display:flex;align-items:center;justify-content:space-between;">
        <div style="width:210px;text-align:center;">
          <div style="margin:0 auto;width:118px;height:210px;border:4px solid ${C.ink};border-radius:24px;background:${C.surface};display:flex;align-items:center;justify-content:center;">
            <p style="font-size:58px;font-weight:700;color:${C.cyan};">1</p>
          </div>
          <h3 style="margin-top:18px;">ChatGPT app</h3><p class="small muted" style="margin-top:6px;">声とテキストで指示</p>
        </div>
        <p style="font-size:54px;color:${C.line};">→</p>
        <div class="card" style="width:250px;height:210px;text-align:center;display:flex;flex-direction:column;justify-content:center;">
          <p class="tiny amber">CONNECTED MAC MINI</p><h2 style="font-size:38px;margin-top:18px;">Codex</h2><p class="small muted" style="margin-top:12px;">読む・作る・試す</p>
        </div>
        <p style="font-size:54px;color:${C.line};">→</p>
        <div class="card" style="width:250px;height:210px;text-align:center;display:flex;flex-direction:column;justify-content:center;">
          <p class="tiny purple">SOURCE OF TRUTH</p><h2 style="font-size:38px;margin-top:18px;">GitHub</h2><p class="small muted" style="margin-top:12px;">spec・code・evidence</p>
        </div>
        <p style="font-size:54px;color:${C.line};">→</p>
        <div class="card" style="width:210px;height:210px;text-align:center;display:flex;flex-direction:column;justify-content:center;border-color:${C.green};">
          <p class="tiny green">PRODUCTION</p><h2 style="font-size:38px;margin-top:18px;">Cloud</h2><p class="small muted" style="margin-top:12px;">常時稼働</p>
        </div>
      </div>
      <div style="position:absolute;left:245px;top:570px;width:790px;text-align:center;">
        <p style="font-size:28px;font-weight:700;">PCを操作するのではなく、<span class="accent">エージェントを運用する</span>。</p>
      </div>
    `),
  },
  {
    note: 'DAILY organの理想体験。ユーザーが開く画面より、向こうから来る電話と報告が主UI。',
    html: frame(5, `
      <div class="title"><p class="kicker">A DAY WITH LIFE MANAGER</p><h2>生活は「画面を開く」前に動く</h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:88px;top:222px;width:1104px;height:330px;">
        <div style="position:absolute;left:30px;right:30px;top:81px;height:4px;background:${C.line};"></div>
        ${[
          ['1','予定を書く','calendar','予定を解釈'],
          ['2','移動を埋める','travel','起点から逆算'],
          ['3','電話が鳴る','T-10 / T-5','出るまで促す'],
          ['4','遅刻を連絡','email','位置で確定後'],
          ['5','事後報告','Telegram','聞かずに報告'],
        ].map((x,i)=>`
          <div style="position:absolute;left:${i*220}px;top:0;width:224px;text-align:center;">
            <div class="numCircle" style="margin:0 auto;background:${i<3?C.cyan:(i===3?C.amber:C.green)};"><p>${x[0]}</p></div>
            <h3 style="margin-top:26px;">${x[1]}</h3>
            <p class="tiny ${i===3?'amber':i===4?'green':'accent'}" style="margin-top:9px;font-weight:700;">${x[2]}</p>
            <p class="small muted" style="margin-top:10px;">${x[3]}</p>
          </div>`).join('')}
      </div>
      <div class="card" style="position:absolute;left:260px;top:556px;width:760px;padding:18px;text-align:center;border-color:${C.cyan};">
        <p class="small">主UIは <span class="accent">電話 + Telegram</span>。Webは許可・停止・証拠を見るコントロールパネル。</p>
      </div>
    `),
  },
  {
    note: '完成済みと本番実証済みを分けない。正本では、DAILY核・電話・パネル認証・スコア・プライバシーがproduction L3済み。',
    html: frame(6, `
      <div class="title"><p class="kicker">BUILT & VERIFIED</p><h2>ここまでは、もう<span class="green">動いている</span></h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:72px;top:192px;width:1136px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">
        ${[
          ['DAILY CORE','予定・travel・call・報告','production依存 9/9'],
          ['VOICE','Telnyx + Gemini Live','実通話・録音'],
          ['PANEL','恒久 /panel + 個人session','TG/Web 2入口'],
          ['CONTROL','接続・通知・call設定','chat/panel同一state'],
          ['SCORES','4 organ outcome score','0件は insufficient'],
          ['PRIVACY','raw log・secret非表示','mobile/desktop実証'],
        ].map((x,i)=>`
          <div class="card" style="height:160px;border-top:4px solid ${i<2?C.cyan:i<4?C.green:C.purple};">
            <p class="tiny ${i<2?'accent':i<4?'green':'purple'}">${x[0]}</p>
            <h3 style="margin-top:12px;">${x[1]}</h3>
            <p class="small muted" style="margin-top:10px;">${x[2]}</p>
          </div>`).join('')}
      </div>
      <div style="position:absolute;left:72px;top:610px;width:1136px;display:flex;justify-content:space-between;">
        <p class="tiny muted">L3 = 実世界のside effectを、実物のreceiptで確認</p>
        <p class="tiny green" style="font-weight:700;">API 200だけでは「完了」にしない</p>
      </div>
    `),
  },
  {
    note: 'システム構造。頭脳の下に三臓器、共有実行基盤、外部世界がある。チャネルはambient first。',
    html: frame(7, `
      <div class="title"><p class="kicker">ARCHITECTURE</p><h2>1つの頭脳が、3つの臓器と外部世界を動かす</h2></div>
      <div class="rule"></div>
      <div class="card" style="position:absolute;left:170px;top:188px;width:940px;height:86px;text-align:center;border-color:${C.cyan};">
        <p class="tiny accent">BRAIN</p><h3 style="margin-top:8px;">intent / context / consent / budget / evidence / ROI</h3>
      </div>
      <div style="position:absolute;left:170px;top:296px;width:940px;display:flex;gap:18px;">
        <div class="card" style="width:301px;height:104px;text-align:center;border-color:${C.green};"><p class="tiny green">PHYSICAL</p><h3 style="margin-top:13px;">予約・健康行動</h3></div>
        <div class="card" style="width:301px;height:104px;text-align:center;border-color:${C.purple};"><p class="tiny purple">MENTAL</p><h3 style="margin-top:13px;">習慣・睡眠・支援</h3></div>
        <div class="card" style="width:301px;height:104px;text-align:center;border-color:${C.amber};"><p class="tiny amber">FINANCIAL</p><h3 style="margin-top:13px;">稼ぐ・払う・送る</h3></div>
      </div>
      <div class="card" style="position:absolute;left:170px;top:424px;width:940px;height:88px;text-align:center;">
        <p class="tiny muted">RUNTIME</p><h3 style="margin-top:10px;">scheduler / browser / email / voice / wallet / eval / ledger</h3>
      </div>
      <div style="position:absolute;left:170px;top:536px;width:940px;display:flex;gap:18px;">
        <div class="chip" style="flex:1;justify-content:center;"><p>電話</p></div>
        <div class="chip" style="flex:1;justify-content:center;"><p>Telegram</p></div>
        <div class="chip" style="flex:1;justify-content:center;"><p>Calendar</p></div>
        <div class="chip" style="flex:1;justify-content:center;"><p>Email / Web</p></div>
        <div class="chip" style="flex:1;justify-content:center;"><p>Panel</p></div>
      </div>
    `),
  },
  {
    note: 'ユーザー体験はambient first。パネルは主役ではなく、鏡とコントロールセンター。',
    html: frame(8, `
      <div class="title"><p class="kicker">UX PRINCIPLE</p><h2>行動は向こうから。設定と証拠は<span class="accent">1枚の鏡</span>に。</h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:82px;top:208px;width:1116px;height:360px;display:flex;gap:24px;">
        <div class="card" style="width:430px;height:360px;border-color:${C.cyan};">
          <p class="tiny accent">AMBIENT CHANNELS</p>
          <h2 style="font-size:42px;margin-top:22px;">電話 + Telegram</h2>
          <p class="small muted" style="margin-top:26px;">起こす。出発を促す。連絡する。予約する。終わったら報告する。</p>
          <div class="chip status-live" style="margin-top:38px;"><p>向こうから来る</p></div>
        </div>
        <div class="card" style="width:662px;height:360px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div><p class="tiny purple">PERSONAL CONTROL PANEL</p><h2 style="font-size:38px;margin-top:14px;">/panel</h2></div>
            <div class="chip status-live"><p>PRODUCTION</p></div>
          </div>
          <div style="margin-top:30px;display:grid;grid-template-columns:1fr 1fr;gap:14px;">
            ${['今日のtimeline','3 organ score','収益・送金台帳','context gate','接続と権限','停止・ON/OFF'].map((x,i)=>`
              <div style="height:58px;border-radius:12px;background:${C.surface2};border:1px solid ${C.line};padding:16px 18px;">
                <p class="small" style="font-size:17px;">${x}</p>
              </div>`).join('')}
          </div>
        </div>
      </div>
    `),
  },
  {
    note: '自己改善の核はループ。観測、評価、行動、実世界検証、学習。失敗時は黙らず、止めて修復し、同じ失敗をテストに変える。',
    html: frame(9, `
      <div class="title"><p class="kicker">SELF-IMPROVING / SELF-HEALING</p><h2>人間がログを見る仕事を、<span class="purple">ループに返す</span></h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:86px;top:222px;width:1108px;height:300px;display:flex;align-items:center;justify-content:space-between;">
        ${[
          ['1','観測','log / metric'],
          ['2','評価','eval / judge'],
          ['3','行動','tool / PR'],
          ['4','実証','receipt / E2E'],
          ['5','学習','lesson / test'],
        ].map((x,i)=>`
          <div style="display:flex;align-items:center;">
            <div class="card" style="width:178px;height:178px;text-align:center;border-color:${[C.cyan,C.purple,C.amber,C.green,C.coral][i]};">
              <p class="tiny" style="color:${[C.cyan,C.purple,C.amber,C.green,C.coral][i]};">${x[0]}</p>
              <h3 style="margin-top:18px;font-size:28px;">${x[1]}</h3>
              <p class="tiny muted" style="margin-top:14px;">${x[2]}</p>
            </div>
            ${i<4?`<p style="font-size:40px;color:${C.line};margin:0 12px;">→</p>`:''}
          </div>`).join('')}
      </div>
      <div class="card" style="position:absolute;left:194px;top:534px;width:892px;height:80px;padding:18px 24px;display:flex;align-items:center;justify-content:space-between;border-color:${C.coral};">
        <p class="small coral" style="font-weight:700;">失敗したら</p>
        <p class="small">exit 0にしない → 原因を特定 → testへ固定 → 修復 → 再実証</p>
      </div>
    `),
  },
  {
    note: '今日のライブ状況。CodexのLife Managerスレッドはactive。ローカル正本のカーソルは8iだが、ライブスレッドはより新しいH3/H5等のキューを処理中。push前の差を混同しない。',
    html: frame(10, `
      <div class="title"><p class="kicker">LIVE STATUS / 2026-07-28</p><h2>別のLife Managerエージェントは、<span class="green">現在も稼働中</span></h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:72px;top:196px;width:1136px;display:flex;gap:22px;">
        <div class="card" style="width:430px;height:382px;border-color:${C.amber};">
          <div class="chip status-next"><p>LOCAL SSOT CURSOR</p></div>
          <h2 style="font-size:52px;margin-top:30px;">8i</h2>
          <h3 style="margin-top:8px;">ONE-REPO 統合</h3>
          <p class="small muted" style="margin-top:24px;">anicca-products から<br>life-manager へ正本を一本化</p>
          <p class="tiny amber" style="margin-top:30px;">push済み正本で確認した位置</p>
        </div>
        <div class="card" style="width:684px;height:382px;border-color:${C.green};">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div class="chip status-live"><p>CODEX THREAD: ACTIVE</p></div>
            <p class="tiny muted">live queue</p>
          </div>
          <div style="margin-top:28px;display:grid;grid-template-columns:1fr 1fr;gap:13px;">
            ${[
              ['H3','checkup spec → builder'],
              ['H5','relations'],
              ['9d','Day 2–7 / self-build台帳'],
              ['11a','scan → 11b → 11c'],
              ['OPS','diet / precepts 初配信'],
              ['TELNYX','残高の自動回復'],
            ].map(x=>`
              <div style="height:82px;border-radius:12px;background:${C.surface2};border:1px solid ${C.line};padding:14px 16px;">
                <p class="tiny green">${x[0]}</p><p class="small" style="font-size:20px;margin-top:7px;">${x[1]}</p>
              </div>`).join('')}
          </div>
        </div>
      </div>
      <p class="tiny muted" style="position:absolute;left:72px;top:605px;">この差は「未push / 別branchのライブ作業」を正本完了と誤認しないため、意図的に分離表示。</p>
    `),
  },
  {
    note: '正本の残TODOをフェーズで示す。目先は統合。次に獲得と自己修復。最後に各臓器を完成させる。',
    html: frame(11, `
      <div class="title"><p class="kicker">REMAINING ROADMAP</p><h2>残りは、上から<span class="amber">この順番</span></h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:72px;top:198px;width:1136px;height:400px;display:grid;grid-template-columns:1fr 1fr;gap:14px 18px;">
        ${[
          ['NOW','8i','ONE-REPO','repo・product・deployを一本化',C.amber],
          ['NEXT','9b–9f','MARKETING','動画生成→配信→計測→改善',C.cyan],
          ['03','10a–10f','DEV LOOP','feedback/error→PR→自動修復',C.purple],
          ['04','10g–10i','BRAIN','intent-aware context graph',C.cyan],
          ['05','11a–11d','PHYSICAL','未ケア検知→候補→予約',C.green],
          ['06','12a–12c','MENTAL','文脈駆動の介入',C.purple],
          ['07','13a–13d','FINANCIAL','wallet→収益→送金',C.amber],
          ['GATE','8e / 8f','CORE L3','inbox readback / real location',C.coral],
        ].map(x=>`
          <div class="card" style="height:92px;padding:15px 18px;display:flex;align-items:center;border-left:6px solid ${x[4]};">
            <div style="width:102px;"><p class="tiny" style="color:${x[4]};font-weight:700;">${x[0]}</p><p class="small" style="margin-top:7px;font-weight:700;white-space:nowrap;">${x[1]}</p></div>
            <div style="width:145px;"><h3 style="font-size:20px;">${x[2]}</h3></div>
            <div style="flex:1;"><p class="small muted" style="font-size:18px;">${x[3]}</p></div>
          </div>`).join('')}
      </div>
    `),
  },
  {
    note: '自律性は無制限な自由ではない。委任範囲、可逆性、コスト、リスク、証拠でゲートする。質問を減らすことと、嘘をつかないことを両立する。',
    html: frame(12, `
      <div class="title"><p class="kicker">AUTONOMY WITH GUARDRAILS</p><h2>自律 = 勝手に動くことではない</h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:72px;top:206px;width:1136px;display:flex;gap:20px;">
        <div class="card" style="width:365px;height:352px;border-top:6px solid ${C.cyan};">
          <p class="tiny accent">REPORT, DON'T ASK</p>
          <h3 style="margin-top:20px;font-size:29px;">委任内は実行して報告</h3>
          <p class="small muted" style="margin-top:24px;">本人しか決められない時だけ、2〜3択のclosed Qを1回。</p>
          <p class="small" style="margin-top:30px;">同じ質問は二度しない。</p>
        </div>
        <div class="card" style="width:365px;height:352px;border-top:6px solid ${C.amber};">
          <p class="tiny amber">CONTEXT GATES</p>
          <h3 style="margin-top:20px;font-size:29px;">信頼を一段ずつ解錠</h3>
          <p class="small muted" style="margin-top:24px;">calendar → Telegram → location → wallet。</p>
          <p class="small" style="margin-top:30px;">最初に全部を要求しない。</p>
        </div>
        <div class="card" style="width:365px;height:352px;border-top:6px solid ${C.coral};">
          <p class="tiny coral">EVIDENCE, NOT CLAIMS</p>
          <h3 style="margin-top:20px;font-size:29px;">失敗を正直に出す</h3>
          <p class="small muted" style="margin-top:24px;">API 200や自己申告ではなく、録音・Message-ID・tx hash・投稿URLで証明。</p>
          <p class="small" style="margin-top:30px;">黙って放置しない。</p>
        </div>
      </div>
    `),
  },
  {
    note: '長期ビジョン。AIが外部経済から収益を得て、自分の計算資源を払い、ユーザー負担を下げる。これは現状では北極星であり、実績と分けて語る。',
    html: frame(13, `
      <div class="title"><p class="kicker">THE DESTINATION</p><h2>AIが自分の<span class="amber">食費と家賃</span>を払う</h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:88px;top:218px;width:1104px;height:282px;display:flex;align-items:center;justify-content:space-between;">
        ${[
          ['外部経済','仕事・販売','EXTERNAL'],
          ['AIが稼ぐ','wallet + ledger','EARN'],
          ['自分を維持','model + cloud','PAY'],
          ['人を支える','body / mind / finance','SERVE'],
          ['負担を縮める','subscription → ¥0','FREE'],
        ].map((x,i)=>`
          <div style="display:flex;align-items:center;">
            <div class="card" style="width:180px;height:184px;text-align:center;border-color:${[C.cyan,C.amber,C.purple,C.green,C.coral][i]};">
              <p class="tiny" style="color:${[C.cyan,C.amber,C.purple,C.green,C.coral][i]};">${x[2]}</p>
              <h3 style="margin-top:18px;">${x[0]}</h3>
              <p class="tiny muted" style="margin-top:15px;">${x[1]}</p>
            </div>
            ${i<4?`<p style="font-size:36px;color:${C.line};margin:0 9px;">→</p>`:''}
          </div>`).join('')}
      </div>
      <div style="position:absolute;left:180px;top:536px;width:920px;text-align:center;">
        <p style="font-size:34px;font-weight:700;">1人 + 1台のスマホ + Life Manager</p>
        <p class="small muted" style="margin-top:14px;">精神的に、身体的に、経済的に健康な人生をオートパイロットへ</p>
      </div>
      <div class="chip status-vision" style="position:absolute;right:72px;top:596px;"><p>VISION</p></div>
    `),
  },
  {
    note: '締め。Life ManagerはUIではなく、生活を観測し、行動し、実証し、学ぶオペレーター。',
    html: frame(14, `
      <div style="position:absolute;left:88px;top:112px;width:1104px;">
        <p class="kicker">ONE SENTENCE</p>
        <h1 style="margin-top:36px;font-size:72px;">Life Managerは<br><span class="accent">アプリではない。</span></h1>
        <h2 style="margin-top:34px;font-size:46px;color:${C.muted};">人生を観測し、動かし、証明し、学ぶ<br>自律オペレーターである。</h2>
      </div>
      <div style="position:absolute;left:88px;top:562px;display:flex;gap:14px;">
        <div class="chip status-live"><p>BUILT: DAILY + PANEL</p></div>
        <div class="chip status-next"><p>NEXT: REPO + LOOPS</p></div>
        <div class="chip status-vision"><p>VISION: SELF-FUNDED LIFE OS</p></div>
      </div>
    `),
  },
];

async function build() {
  fs.mkdirSync(HTML_DIR, { recursive: true });
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.author = 'Daisuke Narita / Codex';
  pptx.subject = 'Life Manager lightning talk';
  pptx.title = 'Life Manager — 理想の生活が向こうから来る';
  pptx.company = 'Life Manager';
  pptx.lang = 'ja-JP';
  pptx.theme = {
    headFontFace: 'Arial',
    bodyFontFace: 'Arial',
    lang: 'ja-JP',
  };

  for (let i = 0; i < slides.length; i += 1) {
    const htmlPath = path.join(HTML_DIR, `slide-${String(i + 1).padStart(2, '0')}.html`);
    fs.writeFileSync(htmlPath, slides[i].html, 'utf8');
    const { slide } = await html2pptx(htmlPath, pptx);
    slide.addNotes(slides[i].note);
  }

  await pptx.writeFile({ fileName: OUT });
  process.stdout.write(`${OUT}\n`);
}

build().catch((error) => {
  console.error(error);
  process.exit(1);
});
