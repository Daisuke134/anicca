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
    note: '今日は、Life Managerで何を任せられるようにしたいのか、いま何が動いていて、何が残っているのかを話す。',
    html: frame(1, `
      <div style="position:absolute;left:72px;top:68px;width:720px;">
        <p class="kicker">LIFE MANAGER / LIGHTNING TALK</p>
        <h1 style="margin-top:28px;">予定も連絡も、<br><span class="accent">先回りして終わらせる。</span></h1>
        <p class="muted" style="margin-top:28px;width:650px;">スマホから指示を出し、Life Managerが予定、健康、お金の用事を片づける</p>
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
    note: '自分は、次の予定、出発時刻、予約、連絡をずっと気にしている。小さな用事でも、忘れないように抱えているだけで疲れる。',
    html: frame(2, `
      <div class="title"><p class="kicker">いま困っていること</p><h2>暮らしには、<span class="coral">覚えておく用事が多い</span></h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:76px;top:205px;width:1128px;height:380px;">
        <div class="card" style="position:absolute;left:0;top:0;width:260px;height:150px;">
          <p class="tiny coral">予定</p><h3 style="margin-top:12px;">次は何時？</h3><p class="small muted" style="margin-top:10px;">何度も時計を見る</p>
        </div>
        <div class="card" style="position:absolute;right:0;top:0;width:260px;height:150px;">
          <p class="tiny amber">移動</p><h3 style="margin-top:12px;">何時に出る？</h3><p class="small muted" style="margin-top:10px;">毎回、自分で逆算</p>
        </div>
        <div class="card" style="position:absolute;left:0;bottom:0;width:260px;height:150px;">
          <p class="tiny purple">健康</p><h3 style="margin-top:12px;">予約しなきゃ</h3><p class="small muted" style="margin-top:10px;">気づくと来週</p>
        </div>
        <div class="card" style="position:absolute;right:0;bottom:0;width:260px;height:150px;">
          <p class="tiny green">お金</p><h3 style="margin-top:12px;">もっと稼がなきゃ</h3><p class="muted" style="margin-top:10px;font-size:20px;line-height:1.3;">考えるだけで終わる</p>
        </div>
        <div style="position:absolute;left:404px;top:77px;width:320px;height:226px;border:2px solid ${C.cyan};border-radius:28px;background:${C.surface2};display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;">
          <p class="kicker">頭から離れない</p>
          <h2 style="font-size:42px;margin-top:18px;">ずっと気になる</h2>
          <p class="muted" style="margin-top:12px;font-size:18px;line-height:1.35;">一日中、気が休まらない</p>
        </div>
      </div>
    `),
  },
  {
    note: 'Life Managerには、身体、心、お金の用事を任せたい。予定、場所、本人の希望をまとめて見て、次に片づけることを決める。',
    html: frame(3, `
      <div class="title"><p class="kicker">任せたいこと</p><h2>Life Managerが扱う<span class="accent">3つの領域</span></h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:72px;top:205px;width:1136px;display:flex;gap:22px;">
        <div class="card" style="width:364px;height:310px;border-top:6px solid ${C.green};">
          <p class="tiny green">身体</p><h2 style="font-size:42px;margin-top:18px;">健康</h2>
          <p class="small muted" style="margin-top:22px;">通院やケアの抜けを探し、空いている時間に予約する。</p>
          <p class="small" style="margin-top:26px;">「木曜18時、歯医者を取った」</p>
        </div>
        <div class="card" style="width:364px;height:310px;border-top:6px solid ${C.purple};">
          <p class="tiny purple">心</p><h2 style="font-size:42px;margin-top:18px;">気持ち</h2>
          <p class="small muted" style="margin-top:22px;">予定と場所を見て、必要になる直前に連絡する。</p>
          <p class="small" style="margin-top:26px;">「準備は全部入ってる」</p>
        </div>
        <div class="card" style="width:364px;height:310px;border-top:6px solid ${C.amber};">
          <p class="tiny amber">お金</p><h2 style="font-size:42px;margin-top:18px;">収入</h2>
          <p class="small muted" style="margin-top:22px;">AIが仕事で得た収入から、クラウド代を払い、残りを送る。</p>
          <p class="small" style="margin-top:26px;">「今月 $120 稼いだ」</p>
        </div>
      </div>
      <div style="position:absolute;left:310px;top:554px;width:660px;text-align:center;">
        <p class="small"><span class="accent">判断：</span>予定、場所、本人の希望を見て、次に片づける用事を決める</p>
      </div>
    `),
  },
  {
    note: '開発の指示はChatGPTのiPhoneアプリから出している。Mac miniに接続したCodexがコードを読み、作り、試し、GitHubへ残す。',
    html: frame(4, `
      <div class="title"><p class="kicker">開発方法</p><h2>開発の指示は、すべて<span class="amber">スマホから</span></h2></div>
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
          <p class="tiny purple">記録</p><h2 style="font-size:38px;margin-top:18px;">GitHub</h2><p class="small muted" style="margin-top:12px;">仕様・コード・実行結果</p>
        </div>
        <p style="font-size:54px;color:${C.line};">→</p>
        <div class="card" style="width:210px;height:210px;text-align:center;display:flex;flex-direction:column;justify-content:center;border-color:${C.green};">
          <p class="tiny green">本番</p><h2 style="font-size:38px;margin-top:18px;">Cloud</h2><p class="small muted" style="margin-top:12px;">いつでも動く</p>
        </div>
      </div>
      <div style="position:absolute;left:245px;top:570px;width:790px;text-align:center;">
        <p style="font-size:28px;font-weight:700;">Mac miniにつないだCodexへ、<span class="accent">ChatGPTアプリから話しかける</span>。</p>
      </div>
    `),
  },
  {
    note: '本人は予定を入れる。Life Managerは移動時間を足し、必要なら電話し、遅刻の連絡を送り、最後にTelegramで結果を知らせる。',
    html: frame(5, `
      <div class="title"><p class="kicker">毎日の使い方</p><h2>予定を書いた後は、Life Managerが動く</h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:88px;top:222px;width:1104px;height:330px;">
        <div style="position:absolute;left:30px;right:30px;top:81px;height:4px;background:${C.line};"></div>
        ${[
          ['1','予定を入れる','カレンダー','内容を読み取る'],
          ['2','移動を追加','出発時刻','出発地から逆算'],
          ['3','電話で起こす','10分前・5分前','出るまで知らせる'],
          ['4','遅刻を連絡','メール','位置を確認して送る'],
          ['5','結果を知らせる','Telegram','終わった内容を報告'],
        ].map((x,i)=>`
          <div style="position:absolute;left:${i*220}px;top:0;width:224px;text-align:center;">
            <div class="numCircle" style="margin:0 auto;background:${i<3?C.cyan:(i===3?C.amber:C.green)};"><p>${x[0]}</p></div>
            <h3 style="margin-top:26px;">${x[1]}</h3>
            <p class="tiny ${i===3?'amber':i===4?'green':'accent'}" style="margin-top:9px;font-weight:700;">${x[2]}</p>
            <p class="small muted" style="margin-top:10px;">${x[3]}</p>
          </div>`).join('')}
      </div>
      <div class="card" style="position:absolute;left:260px;top:556px;width:760px;padding:18px;text-align:center;border-color:${C.cyan};">
        <p class="small">普段は <span class="accent">電話とTelegram</span>。Webは、許可、停止、実行結果の確認に使う。</p>
      </div>
    `),
  },
  {
    note: '予定、電話、個人パネル、設定、結果の集計、画面の安全対策は、本番で実物を使って確認した。APIが成功を返しただけでは完了にしていない。',
    html: frame(6, `
      <div class="title"><p class="kicker">現在地</p><h2><span class="green">本番で動いている</span>もの</h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:72px;top:192px;width:1136px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">
        ${[
          ['毎日の予定','予定・移動・電話・報告','本番の依存先 9/9'],
          ['電話','Telnyx + Gemini Live','実際に通話・録音'],
          ['個人パネル','/panel + 個人認証','Telegram / Web'],
          ['設定','接続・通知・電話','2画面で同じ状態'],
          ['結果の集計','4領域の結果を集計','対象0件も区別'],
          ['画面の安全','ログ・秘密情報を隠す','スマホ / PCで確認'],
        ].map((x,i)=>`
          <div class="card" style="height:160px;border-top:4px solid ${i<2?C.cyan:i<4?C.green:C.purple};">
            <p class="tiny ${i<2?'accent':i<4?'green':'purple'}">${x[0]}</p>
            <h3 style="margin-top:12px;">${x[1]}</h3>
            <p class="small muted" style="margin-top:10px;">${x[2]}</p>
          </div>`).join('')}
      </div>
      <div style="position:absolute;left:72px;top:610px;width:1136px;display:flex;justify-content:space-between;">
        <p class="tiny muted">L3 = 本物の電話、メール、Message-IDなどで結果を確認</p>
        <p class="tiny green" style="font-weight:700;">APIが200を返しただけでは完了にしない</p>
      </div>
    `),
  },
  {
    note: '本人の希望、予定、場所、許可、予算、過去の結果を見て、健康、心、お金のどれを処理するか決める。実行にはブラウザ、メール、電話などを使う。',
    html: frame(7, `
      <div class="title"><p class="kicker">仕組み</p><h2>Life Managerの<span class="accent">処理の流れ</span></h2></div>
      <div class="rule"></div>
      <div class="card" style="position:absolute;left:170px;top:188px;width:940px;height:86px;text-align:center;border-color:${C.cyan};">
        <p class="tiny accent">判断に使う情報</p><h3 style="margin-top:8px;">本人の希望 / 予定 / 場所 / 許可 / 予算 / 過去の結果</h3>
      </div>
      <div style="position:absolute;left:170px;top:296px;width:940px;display:flex;gap:18px;">
        <div class="card" style="width:301px;height:104px;text-align:center;border-color:${C.green};"><p class="tiny green">健康</p><h3 style="margin-top:13px;">予約・健康行動</h3></div>
        <div class="card" style="width:301px;height:104px;text-align:center;border-color:${C.purple};"><p class="tiny purple">心</p><h3 style="margin-top:13px;">習慣・睡眠・支援</h3></div>
        <div class="card" style="width:301px;height:104px;text-align:center;border-color:${C.amber};"><p class="tiny amber">お金</p><h3 style="margin-top:13px;">稼ぐ・払う・送る</h3></div>
      </div>
      <div class="card" style="position:absolute;left:170px;top:424px;width:940px;height:88px;text-align:center;">
        <p class="tiny muted">実行する手段</p><h3 style="margin-top:10px;">定期実行 / ブラウザ / メール / 電話 / ウォレット / 評価 / 記録</h3>
      </div>
      <div style="position:absolute;left:170px;top:536px;width:940px;display:flex;gap:18px;">
        <div class="chip" style="flex:1;justify-content:center;"><p>電話</p></div>
        <div class="chip" style="flex:1;justify-content:center;"><p>Telegram</p></div>
        <div class="chip" style="flex:1;justify-content:center;"><p>カレンダー</p></div>
        <div class="chip" style="flex:1;justify-content:center;"><p>メール / Web</p></div>
        <div class="chip" style="flex:1;justify-content:center;"><p>個人パネル</p></div>
      </div>
    `),
  },
  {
    note: '普段の連絡は電話とTelegramで受け取る。個人パネルは毎日開く画面ではなく、設定を変えたり、実行結果を確かめたりするときに使う。',
    html: frame(8, `
      <div class="title"><p class="kicker">使う画面</p><h2>本人への連絡と、<span class="accent">確認画面</span></h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:82px;top:208px;width:1116px;height:360px;display:flex;gap:24px;">
        <div class="card" style="width:430px;height:360px;border-color:${C.cyan};">
          <p class="tiny accent">ふだん使う</p>
          <h2 style="font-size:42px;margin-top:22px;">電話 + Telegram</h2>
          <p class="small muted" style="margin-top:26px;">起こす。出発を促す。連絡する。予約する。終わったら報告する。</p>
          <div class="chip status-live" style="margin-top:38px;"><p>必要なときに届く</p></div>
        </div>
        <div class="card" style="width:662px;height:360px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div><p class="tiny purple">確認と設定</p><h2 style="font-size:38px;margin-top:14px;">/panel</h2></div>
            <div class="chip status-live"><p>本番稼働中</p></div>
          </div>
          <div style="margin-top:30px;display:grid;grid-template-columns:1fr 1fr;gap:14px;">
            ${['今日の予定','3領域の結果','収益と送金','判断に使った情報','接続と権限','停止と再開'].map((x,i)=>`
              <div style="height:58px;border-radius:12px;background:${C.surface2};border:1px solid ${C.line};padding:16px 18px;">
                <p class="small" style="font-size:17px;">${x}</p>
              </div>`).join('')}
          </div>
        </div>
      </div>
    `),
  },
  {
    note: 'ログと数値から失敗を見つけ、原因を調べ、コードを直し、本物の電話やメールで確認する。同じ失敗はテストに残す。',
    html: frame(9, `
      <div class="title"><p class="kicker">自動修復</p><h2>失敗を見つけて、直し、<span class="purple">次を防ぐ</span></h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:86px;top:222px;width:1108px;height:300px;display:flex;align-items:center;justify-content:space-between;">
        ${[
          ['1','観測','ログ・数値'],
          ['2','判定','合格 / 失敗'],
          ['3','修正','コード・PR'],
          ['4','確認','実物で試す'],
          ['5','再発防止','テストに残す'],
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
        <p class="small">成功扱いしない → 原因を探す → テストを追加 → 修正 → もう一度動かす</p>
      </div>
    `),
  },
  {
    note: 'GitHubで確認できる正本は8i。別のCodexスレッドでは、その先の作業も進んでいる。ただし、未pushや別ブランチの作業は完了扱いにしない。',
    html: frame(10, `
      <div class="title"><p class="kicker">進行中の作業 / 2026-07-28</p><h2>別のCodexスレッドで、<span class="green">開発は続いている</span></h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:72px;top:196px;width:1136px;display:flex;gap:22px;">
        <div class="card" style="width:430px;height:382px;border-color:${C.amber};">
          <div class="chip status-next"><p>PUSH済みの正本</p></div>
          <h2 style="font-size:52px;margin-top:30px;">8i</h2>
          <h3 style="margin-top:8px;">リポジトリ統合</h3>
          <p class="small muted" style="margin-top:24px;">anicca-products から<br>life-manager へ正本を一本化</p>
          <p class="tiny amber" style="margin-top:30px;">GitHubで確認した位置</p>
        </div>
        <div class="card" style="width:684px;height:382px;border-color:${C.green};">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div class="chip status-live"><p>CODEXスレッド：稼働中</p></div>
            <p class="tiny muted">いま処理中</p>
          </div>
          <div style="margin-top:28px;display:grid;grid-template-columns:1fr 1fr;gap:13px;">
            ${[
              ['H3','健康診断の仕様 → 実装'],
              ['H5','人間関係'],
              ['9d','2〜7日目の収益台帳'],
              ['11a','検知 → 候補 → 予約'],
              ['運用','食事 / 戒律 初回配信'],
              ['TELNYX','残高の自動補充'],
            ].map(x=>`
              <div style="height:82px;border-radius:12px;background:${C.surface2};border:1px solid ${C.line};padding:14px 16px;">
                <p class="tiny green">${x[0]}</p><p class="small" style="font-size:20px;margin-top:7px;">${x[1]}</p>
              </div>`).join('')}
          </div>
        </div>
      </div>
      <p class="tiny muted" style="position:absolute;left:72px;top:605px;">右側には未pushや別ブランチの作業も含む。ここでは完了扱いにしない。</p>
    `),
  },
  {
    note: '残作業はこの順番で進める。まずリポジトリを一本化し、集客と開発の自動修復を作る。その後、健康、心、お金の機能を仕上げる。',
    html: frame(11, `
      <div class="title"><p class="kicker">残作業</p><h2><span class="amber">残っている作業</span>と、その順番</h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:72px;top:198px;width:1136px;height:400px;display:grid;grid-template-columns:1fr 1fr;gap:14px 18px;">
        ${[
          ['最優先','8i','リポジトリ統合','正本・実装・配備先を一本化',C.amber],
          ['その次','9b–9f','集客','動画作成→投稿→計測→修正',C.cyan],
          ['03','10a–10f','開発の自動修復','不具合→PR→配備→回復確認',C.purple],
          ['04','10g–10i','判断','予定と本人の意図から次を選ぶ',C.cyan],
          ['05','11a–11d','健康','未ケア検知→候補→予約',C.green],
          ['06','12a–12c','心','予定と場所に合わせて連絡',C.purple],
          ['07','13a–13d','お金','収入→支払い→送金',C.amber],
          ['条件待ち','8e / 8f','本番確認','受信箱の読取り / 実際の位置情報',C.coral],
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
    note: '任せた範囲では、実行してから報告する。権限は必要な分だけ受け取り、実行結果は録音やMessage-IDなどで確認する。失敗も隠さない。',
    html: frame(12, `
      <div class="title"><p class="kicker">安全のためのルール</p><h2>自動化の<span class="accent">境界</span></h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:72px;top:206px;width:1136px;display:flex;gap:20px;">
        <div class="card" style="width:365px;height:352px;border-top:6px solid ${C.cyan};">
          <p class="tiny accent">任せた範囲</p>
          <h3 style="margin-top:20px;font-size:29px;">実行してから報告</h3>
          <p class="small muted" style="margin-top:24px;">本人にしか決められない時だけ、短い選択肢を一度だけ聞く。</p>
          <p class="small" style="margin-top:30px;">同じことは聞かない。</p>
        </div>
        <div class="card" style="width:365px;height:352px;border-top:6px solid ${C.amber};">
          <p class="tiny amber">使える情報</p>
          <h3 style="margin-top:20px;font-size:29px;">権限は必要な分だけ</h3>
          <p class="small muted" style="margin-top:24px;">カレンダー、Telegram、位置情報、ウォレットの順に接続。</p>
          <p class="small" style="margin-top:30px;">最初から全部は求めない。</p>
        </div>
        <div class="card" style="width:365px;height:352px;border-top:6px solid ${C.coral};">
          <p class="tiny coral">実行結果</p>
          <h3 style="margin-top:20px;font-size:29px;">失敗もそのまま伝える</h3>
          <p class="small muted" style="margin-top:24px;">録音、Message-ID、取引ID、投稿URLを確認する。</p>
          <p class="small" style="margin-top:30px;">エラーを隠さない。</p>
        </div>
      </div>
    `),
  },
  {
    note: '長期目標は、AIが仕事で収入を得て、自分のモデル代とサーバー代を払うこと。残りを本人へ送り、利用料を下げる。まだ実績ではなく、今後作る部分。',
    html: frame(13, `
      <div class="title"><p class="kicker">長期目標</p><h2>AI自身が、<span class="amber">運営費を稼ぐ</span></h2></div>
      <div class="rule"></div>
      <div style="position:absolute;left:88px;top:218px;width:1104px;height:282px;display:flex;align-items:center;justify-content:space-between;">
        ${[
          ['仕事をする','販売・受託','仕事'],
          ['収入を受け取る','ウォレット','収入'],
          ['運営費を払う','モデル・サーバー','支払い'],
          ['残りを送る','本人の口座へ','送金'],
          ['利用料を下げる','月額 → 0円','還元'],
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
        <p class="small muted" style="margin-top:14px;">毎日の予定、健康、お金の用事を、スマホ1台から任せられる状態へ</p>
      </div>
      <div class="chip status-vision" style="position:absolute;right:72px;top:596px;"><p>今後</p></div>
    `),
  },
  {
    note: 'Life Managerは、予定と場所を読み、必要な処理を実行し、結果を本人へ伝える。失敗したら原因を調べて直す。そこまでを任せたい。',
    html: frame(14, `
      <div style="position:absolute;left:88px;top:112px;width:1104px;">
        <p class="kicker">LIFE MANAGER</p>
        <h1 style="margin-top:36px;font-size:72px;">暮らしの用事を、<br><span class="accent">先回りして片づける。</span></h1>
        <h2 style="margin-top:34px;font-size:42px;color:${C.muted};">予定と場所を読み、必要な処理を実行する。<br>結果を本人へ伝え、失敗したら直す。</h2>
      </div>
      <div style="position:absolute;left:88px;top:562px;display:flex;gap:14px;">
        <div class="chip status-live"><p>稼働中：予定 + 個人パネル</p></div>
        <div class="chip status-next"><p>次：統合 + 自動修復</p></div>
        <div class="chip status-vision"><p>目標：自分で運営費を稼ぐ</p></div>
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
  pptx.title = 'Life Manager — 暮らしの用事を先回りして片づける';
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
