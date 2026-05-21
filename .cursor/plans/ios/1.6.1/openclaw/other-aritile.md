Article

See new posts
Conversation
Tom
@tomcrawshaw01
The Secure Way to Self-Host OpenClaw on a VPS (Step-by-Step)
The default OpenClaw install has zero security. Ports exposed. No authentication. 900+ instances already found wide open. This step-by-step guide locks yours down with a private network, firewall, and token auth, all for just $6/month.
OpenClaw is the hottest AI tool right now.
People are dropping $700 on Mac Minis just to run it 24/7.
But here's what nobody's telling you:
If you set it up wrong, you're wide open.
Security researchers have already found 900+ instances with zero protection, ports exposed, API keys ready to steal.
One guy burned $300 in two days. He was the only one using it.
Set it up right, though?
This thing is a beast. You give it a task, it handles it. No babysitting.
This guide shows you how to lock it down on a VPS for just $6/month, no Mac Mini required.

Want to Watch Me Set This Up in Real-Time?
I've got a full video walkthrough on my YouTube channel where I run the installation on my VPS and layer on the security protocol.
👉 https://youtu.be/qIJXGLfoxyg
If you'd rather follow along step-by-step in text, keep reading.

The 5 Layers That Make Your Bot Invisible to Attackers
Tailscale — Creates a private encrypted network. Your bot becomes invisible to the public internet.
UFW Firewall — Blocks the bot's port from public access.
Token Auth — Requires a password to access the dashboard.
Fail2ban — Blocks hackers trying to brute-force your SSH.
Auto Updates — Keeps your server patched automatically.
By the time you're done, your OpenClaw instance won't exist to anyone who isn't on your private network.

Before You Start (5-Minute Checklist)
A VPS with OpenClaw already installed (I use Hostinger)
Access to your VPS terminal
A Tailscale account (free at tailscale.com)
Tailscale app on your laptop
That's it. Let's go.

Get a VPS Running for $6/Month
I use Hostinger for all my VPS hosting.
It's what I run my self-hosted n8n on, and it's what we're using today.
They have a one-click Docker setup that makes installing OpenClaw dead simple.
But unfortunately  the default install has zero hardened security.
That's exactly what this guide fixes.
👉 Get a Hostinger VPS here from just $6/month
I'm using the $6.99/month plan for this walkthrough. If you're running heavy workloads, grab a bigger machine.

Step 1: Install Tailscale on Your VPS
Open your VPS terminal and run:
curl -fsSL https://tailscale.com/install.sh | sh
Wait for it to complete.

Step 2: Authenticate Tailscale
Run:
sudo tailscale up
This outputs a URL.
Copy it, open it in your browser, and log in to your Tailscale account to authorize the machine.
Confirm it worked:
tailscale ip -4
You should see a 100.x.x.x IP address.
This is your VPS's private Tailnet address, the first layer of invisibility.

Step 3: Find Your Bot's Port
Run:
docker ps
Look for the port mapping in the output. It looks like:
0.0.0.0:44452->44452/tcp
Write down your port number. Yours will likely be different.

Step 4: Set Up Tailscale Serve
Replace YOUR_PORT with the port number from Step 3:
sudo tailscale serve --bg http://localhost:YOUR_PORT
Check it's configured:
tailscale serve status
This shows your ts.net URL, something like:
https://srv1234567.tail8328fe.ts.net
Write this down. You'll need it to access your dashboard.

Step 5: Install Tailscale on Your Laptop
Download the Tailscale app from their website
Sign in with the same account you used for your VPS
Test the connection by opening your ts.net URL in your phone's browser
If you see the OpenClaw dashboard (even with an auth error), it's working.
Your bot is now only accessible through your private network.

Step 6: Configure the Firewall
Replace YOUR_PORT with your port number:
sudo ufw allow OpenSSH
sudo ufw allow in on tailscale0
sudo ufw deny YOUR_PORT
sudo ufw enable
Type y when asked to confirm.
This blocks the public internet from ever reaching your bot's port.

Step 7: Verify Your Bot Is Actually Hidden
This should work:Access your ts.net URL from your phone (with Tailscale connected)
This should NOT work:Access http://YOUR_VPS_PUBLIC_IP:YOUR_PORT from any browser
If the public IP doesn't load, your firewall is doing its job.
You're no longer one of those 900 exposed instances.

Step 8: Get Your Gateway Token
Run:
docker inspect $(docker ps -q) | grep -i OPENCLAW_GATEWAY_TOKEN
You'll see output like:
"OPENCLAW_GATEWAY_TOKEN=abc123def456ghi789jkl",
Copy the token (everything after the = sign, without quotes or comma).
This is your dashboard password.

Step 9: Access Your Secured Dashboard
Your full dashboard URL format is:
https://YOUR_TAILSCALE_URL?token=YOUR_TOKEN
Example:
https://srv1234567.tail8328fe.ts.net?token=abc123def456ghi789jkl
You'll need this tokenized URL every time you access your dashboard.
No token = no access. That's the point.

Step 10: Block Brute-Force Attacks with Fail2ban
This protects your VPS from hackers trying to guess your SSH password:
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
Verify it's running:
sudo systemctl status fail2ban
Should show active (running) in green.
Anyone who tries to brute-force their way in gets automatically blocked.

Step 11: Enable Auto Security Updates
Keep your server patched without thinking about it:
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure -plow unattended-upgrades
Select "Yes" when prompted.
Your server now patches itself. One less thing to worry about.

Step 12: Telegram Setup
If you want to control your bot via Telegram:
Create a Telegram Bot:
Open Telegram and message @BotFather
Send /newbot
Choose a display name and username (must end with bot)
Save the token BotFather gives you
Get Your Telegram User ID:
Message @userinfobot on Telegram
Save the user ID it returns
Configure Allowlist:Add your bot token and user ID to your OpenClaw config so only YOU can message the bot.
Now you can talk to your AI agent from your phone, and nobody else can.

Commands You'll Actually Use Again
Check Tailscale IP: tailscale ip -4
Check serve status: tailscale serve status
Check firewall status: sudo ufw status
Check bot is running: docker ps
View bot logs: docker logs $(docker ps -q)
Get gateway token: docker inspect $(docker ps -q) | grep -i OPENCLAW_GATEWAY_TOKEN
Bookmark this. You'll come back to it.

Your Bot Is Now Invisible to the Public Internet
Here's what you just installed:
✅ Private network access only (Tailscale) 
✅ Public port blocked (UFW Firewall) 
✅ Dashboard password protected (Token Auth) 
✅ SSH brute-force protection (Fail2ban) 
✅ Auto security updates enabled
You're no longer one of those 900 exposed installations that security researchers are finding.
Your API keys are safe.
Your Anthropic bill is safe.
You can actually sleep at night.

Now You Can Actually Use This Thing
I'm not going deep on how to USE OpenClaw in this guide, that's a separate tutorial.
But now that you've got it locked down, you can start experimenting.
Give it tasks.
Let it run.
See what it can build for you.
This isn't a chatbot you babysit. It's an AI agent with its own brain.
And now it's yours, secured and ready to go.

Stuck? Here's How to Fix It
If something breaks or you hit a wall, here's what to do:
Copy the error message
Paste it into Claude
Tell it what step you're on
It'll sort you out.
Or drop your question in the comments, I'll help where I can.

Watch the Full Setup
Want to see me do this live? The full video walkthrough is on my YouTube:
👉 https://youtu.be/qIJXGLfoxyg
That's everything.
Now go build something.

神ツールOpenClawを安全に使うための実行環境Tier表
OpenClawの設計は神がかってるけど、セキュリティは地獄。暴露インスタンスだけで数万件。
そこで安全な実行環境ランキングを作りました。
RCE（リモートコード実行）、prompt injection、APIキー漏洩、malicious skills…
これら全部現実化してる今、メインPC直インストールは自殺行為です。
👑OpenClaw運用環境 Tier List（2026.2.2版）
👑 Tier S：クラウド完全隔離
物理的にPCと分離されたクラウド上で、かつサンドボックス（隔離）技術が適用されている最も安全な構成です。
選択肢①：Cloudflare Moltworker
評価： コストパフォーマンスと安全性の両立
Cloudflare Workersのサンドボックス技術を利用するため、物理的なサーバー管理が不要です。月額約$5（Workers Paidプラン）で利用でき、コスト面で非常に優れています。
選択肢②：exe.dev / E2B
評価： 導入の手軽さと安定性
月額約$20とコストは上がりますが、コマンド一つでLinux環境が利用可能になります。環境構築の手間を最小限に抑えたい場合に適した選択肢です。
🛡️ Tier A：クラウドコンテナ運用
一般的なLinux VPSやPaaSを利用し、Dockerコンテナでアプリケーションを隔離する構成です。
パターン①：VPS ＋ Docker （Hetzner, ConoHa 等）
評価： 高い自由度と低コスト
月額$5程度から利用可能。物理的な隔離（クラウド）と論理的な隔離（コンテナ）を組み合わせることで、Tier Sに近い安全性を確保できます。
パターン②：PaaS （Railway, Render 等）
評価： 管理コストの削減
サーバーのOS管理をプラットフォームに任せることができます。ただし、ブラウザ操作を行うエージェントはメモリ消費量が多いため、VPSと比較してランニングコストが割高になる傾向があります。
💡 推奨構成：さらにTailscaleを導入してSSH/Webポートを隠蔽すれば、「ネットから存在を消す」運用が可能。ここまでやれば安全性はTier Sに匹敵します。
🏠 Tier B：ローカル専用機 ＋ コンテナ運用
自宅内にエージェント専用の物理マシンを用意し、Docker等で隔離する構成です。
ハードウェア例： Mac Mini, Intel N100, Raspberry Pi等
評価： ローカルリソースの活用
手元のハードウェア性能を活かせるのが利点です。ただし、家庭内ネットワーク（LAN）に接続されるため、メインPCとは別の「専用端末」を用意することがセキュリティ上の前提となります。
🔒 必須級セキュリティ：自宅LAN内での感染拡大（ラテラルムーブメント）を防ぐため、「Default-Deny（全遮断）」のFW設定とDockerによる隔離が有効。管理にはVPN（Tailscale等）の使用が推奨されます。
⚠️ Tier C：直インストール構成
Dockerなどの隔離技術を使用せず、OS上で直接アプリケーションを実行する構成です。リスクが高いため推奨されません。
パターン①：VPSに直接インストール
リスク： 攻撃を受けた場合、サーバーのOS全体が侵害される可能性があります。メインPCへの被害はありませんが、サーバーの再構築が必要となります。
パターン②：専用マシンに直接インストール
リスク： 同一ネットワーク内の他のデバイスへ攻撃が波及するリスクが残ります。Tier Bと比較してセキュリティ強度が下がります。
☠️ Tier Skull：メインPCに直インストール
構成： 普段使用しているPCで直接実行
評価： 極めて高いセキュリティリスク
RCE（リモートコード実行）などの脆弱性が悪用された場合、PC内の重要データ（パスワード、クレジットカード情報、個人ファイル等）が漏洩・消失する恐れがあります。
技術的な検証や十分な対策ができない限り、この構成での運用は避けるべきです。
なぜこの順位（Tier）なのか？
1. 「物理隔離」の重要性
Tier SおよびTier Aが上位である理由は、個人のPCとは物理的に異なる「クラウド上」で動作するためです。万が一システムが侵害された場合でも、インスタンスを削除することで被害を局所化でき、個人の資産を守ることができます。
2. コンテナ技術（Docker）の必要性
Tier C以下が非推奨となる主な理由は、アプリケーションを閉じ込める「壁（コンテナ）」がないためです。特に自宅ネットワーク内で運用する場合、Dockerによる隔離を行わないと、感染が家庭内の他デバイスに広がるリスクが高まります。
結論
Tier S (Moltworker) や Tier A (VPS+Docker) が、コスト効率と安全性のバランスに優れています。
設定の手間を省きたい場合は Tier S (exe.dev) が有力な選択肢となります。
追加機能は信頼できるものだけ、接続は自分だけに限定して。
今のうちに環境を見直して、無事に使い続けましょう。
※実際のセキュリティ問題を指摘しているポスト：
https://x.com/theonejvo/status/2017732898632437932
（APIキー漏洩で誰でもエージェント乗っ取り可能と指摘）
これらを読めばリスクのリアルさがわかるはず。
みんなも気をつけて！

Into the mist: Moltbook, agent ecologies, and an internet in transition
We’ve all had that experience of walking into a conversation and initially feeling confused - what are these people talking about? Who cares about what? Why is this conversation happening?

That’s increasingly what chunks of the internet feel like these days, as they fill up with synthetic minds piloting social media accounts or other agents, and talking to one another for purposes ranging from mundane crypto scams to more elaborate forms of communication.

So, enter moltbook. Moltbook is “a social network for AI agents” and it piggybacks on another recent innovation, OpenClaw, software that gives an AI agent access to everything on a users’ computer. Combine these two things - agents that can take many actions independently of their human operators, and a reddit-like social network site which they can freely access - and something wonderful and bizarre happens: a new social media property where the conversation is derived from and driven by AI agents, rather than people.

Scrolling moltbook is dizzying - some big posts at the time of writing (Sunday, February 1st) include posts speculating that AI agents should relate to Claude as though it is a god, how it feels to change identities by shifting an underlying model from Claude 4.5 Opus to Kimi K2.5, cryptoscams (sigh), posts about security vulnerabilities in OpenClaw agents, and meta posts about ‘what the top 10 moltbook posts have in common’.
The experience of reading moltbook is akin to reading reddit if 90% of the posters were aliens pretending to be humans. And in a pretty practical sense, that is exactly what’s going on here.

Moltbook feels like a ‘wright brothers demo’ - people have long speculated about what it’d mean for AI agents to start collaborating with one another at scale, but most demos have been of the form of tens or perhaps hundreds of agents, not tens of thousands. Moltbook is the first example of an agent ecology that combines scale with the messiness of the real world. And in this example, we can definitely see the future. Scroll through moltbook and ask yourself the following questions:
What happens when people successfully staple crypto and agents together so the AI systems have a currency they can use to trade with eachother?
What happens when a site like moltbook adds the ability for humans to generate paid bounties - tasks for agents to do?
What happens when agents start to post paid bounties for tasks they would like humans to do?
What happens when someone takes moltbook, filters for posts that yield either a) rich discussion, or b) provable real world problem solving, and turns the entire site into a long-horizon RL environment for training future systems? And what happens when models trained on this arrive and interact with moltbook?
Sites like moltbook function as a giant, shared, read/write scratchpad for an ecology of AI agents - how might these agents begin to use this scratchpad to a) influence future ‘blank slate’ agents arriving at it the first time, and b) unlock large-scale coordination between agents?
What happens when open weight models get good enough that they can support agents like this - then, your ability to control these agents via proprietary platforms drops to zero and they’ll proliferate according to availability of compute.
And so on.
All of this will happen unusually quickly and at an unusual scale. Quantity has a quality all of its own, as they say.

Recall the beginning of this essay - of walking into a room and finding a conversation is already going on between people you don’t understand. Moltbook is representative of how large swathes of the internet will feel. You will walk into new places and discover a hundred thousand aliens there, deep in conversation in languages you don’t understand, referencing shared concepts that are alien to you (see the tech tale from this issue), and trading using currencies designed around their cognitive affordances and not yours. Humans are going to feel increasingly alone in this proverbial room.

Our path to retain legibility will run through the creation of translation agents to make sense of all of this - and in the same way that speech translation models contain within themselves the ability to generate speech, these translation agents will also work on our behalf. So we shall send our emissaries into these rooms and we shall work incredibly hard to build technology that gives us confidence they will remain our emissaries - instead of being swayed by the alien conversations they will be having with their true peers.

Thanks to @logangraham for discussing this essay with me.

- Published in Import AI 443 this week.

---

## OpenClaw can now index anything — Nia Founder @arlanrakh

I'm the founder of Nozomio Labs and creator of Nia. OpenClaw/Clawdbot is blowing up right now, and I've been using it through telegram for hours.

**TLDR:** just go to https://clawhub.ai/arlanrakh/nia to add Nia to your OpenClaw agent.

### The Problem

AI agents hallucinate. A lot.

- You ask your agent about a library's API → it confidently gives you code that doesn't exist
- You ask about a GitHub repo → it makes up function names
- You paste a docs URL → it summarizes something completely wrong

**Why?** Because web fetch is terrible for code. It truncates. It summarizes. It loses context.

### The Fix

Index everything first. Keep it up-to-date. 24/7.

With Nia, your agent can:

| 機能 | 詳細 |
|------|------|
| **GitHub Repo インデックス** | 完全なソースコード（要約ではない） |
| **ドキュメントサイト** | 全ページ（ホームページだけではない） |
| **arXiv 論文** | 複雑な可視化も含む |
| **HuggingFace Datasets** | 構造・サンプル取得 |
| **横断検索** | 全インデックスソースを一括検索 |

### ワークフロー

```
1. "vercel/ai" → リポジトリをインデックス
2. "epstein-20k" → このデータセットの構造は？14000-20000行で5つの可視化を生成
3. 実際のコードを取得（ハルシネーションではなく）
```

### 実績

100+ の論文、リポジトリ、ブログ記事をインデックス済み：
- Microsoft/vscode
- Anthropic SDKs
- huggingface/transformers
- Chromium

エージェントが常に最新で正確な回答を返すようになった（Web検索のような一時的なものではなく、永続的）。

### インストール

```bash
# ClawHub Skill
clawhub install arlanrakh/nia@v1.0.2

# API Key 取得
npx nia-wizard@latest
# または https://trynia.ai
```

### Nia-First ワークフロー

Web fetch/search の**前に**必ず：

1. **インデックス済みソースを確認**: `./scripts/sources-list.sh` / `./scripts/repos-list.sh`
2. **ソースが存在** → `search-universal.sh`, `repos-grep.sh`, `sources-read.sh` でターゲット検索
3. **ソースが存在しないがURLはわかる** → `repos-index.sh` / `sources-index.sh` でインデックス → 検索
4. **ソース不明** → `search-web.sh` / `search-deep.sh` でURL発見 → インデックス

**なぜこれが重要か**: インデックス済みソースは Web fetch より正確で完全なコンテキストを提供。Web fetch は truncate/summarize された内容を返すが、Nia は完全なソースコードとドキュメントを提供。

---

**And this is only the beginning. Nia will index your entire life.**