#!/usr/bin/env node

import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

import {
  contextDigest,
  loadStartupContext,
  validatePublicArtifact,
  validateStartupContext,
} from "./lib.mjs";

function metadata(context, digest) {
  return `<!-- generated from .agents/startup-context.json; do not edit -->\ncontext-version: ${context.context_version}\ncontext-digest: ${digest}\n`;
}

function markdownArtifacts(context, digest) {
  const head = metadata(context, digest);
  const product = context.product.name;
  const oneLiner = context.product.one_liner;
  const productUrl = context.links.product.url;
  const repositoryUrl = context.links.repository.url;
  const telegramUrl = context.links.telegram.url;

  return {
    "README.md": `${head}\n# ${product} fundraising application kit\n\nThis directory is generated from the repository-owned startup context. Adapt semantic answers to each program's official questions, but never change product facts, links, evidence, or claims without updating and validating the source context.\n\n- Product: ${product}\n- Product page: ${productUrl}\n- Repository: ${repositoryUrl}\n- Telegram: ${telegramUrl}\n- Demo video: not verified; do not attach\n- Founder video: not verified; do not attach\n\nPast submissions are historical evidence, not a source for new answers.\n`,
    "answers.en.md": `${head}\n# ${product} — canonical fundraising answers\n\n## What is the product?\n\n${oneLiner}\n\n## What does it do?\n\n${product} is a manager, not another chat assistant. Its Daily Organ coordinates schedules and applications. Its Physical / Mental Organ supports routines and wellbeing. Its Financial Organ builds a complete view of assets, cash flow, spending, income opportunities, and risk-managed investing. It acts within delegated boundaries, preserves receipts, and explains the result in Telegram.\n\n## Why now?\n\nModels can reason and use tools, but a person's goals still break across calendars, forms, financial accounts, and dashboards. ${product} connects those surfaces through one evidence ledger and one manager experience.\n\n## What is different?\n\nMost alternatives stop at advice or one dashboard. ${product} executes authorized actions, independently verifies completion, and never reports an attempt as success without evidence. The local and cloud surfaces use the same core.\n\n## How far along is it?\n\nThe repository and Telegram entry point are public. Local and cloud components and specialist loops exist in the repository. User count, revenue, retention, complete bank coverage, investing performance, demo media, and founder video must not be asserted until their current evidence is verified.\n\n## Business model\n\nThe intended model is free local self-hosting plus a paid always-on cloud service. Any future performance-linked financial fee requires separate legal, risk, and user-consent review; it is not a current claim.\n\n## Links\n\n- Product: ${productUrl}\n- Repository: ${repositoryUrl}\n- Telegram: ${telegramUrl}\n`,
    "answers.ja.md": `${head}\n# ${product} — 資金調達応募の正本回答\n\n## 何を作っていますか\n\n${product}は、身体・心・お金を管理し、委任範囲で現実の行動を実行して、証拠付きの結果をTelegramへ返すpersonal managerです。\n\n## 何をしますか\n\nDaily Organは予定と応募を進め、Physical / Mental Organは生活習慣とwellbeingを支え、Financial Organは総資産、収支、支出、収入機会、riskを制御した資産運用を管理します。提案だけで終わらず、許可された行動を実行し、receiptを保存します。\n\n## なぜ今ですか\n\nmodelは推論とtool利用ができる一方、userの目標はCalendar、form、金融口座、dashboardの間で止まります。${product}は一つの証拠台帳とmanager体験でそれらを接続します。\n\n## 何が違いますか\n\n助言や可視化だけで止まりません。委任された行動を実行し、完了を独立検証し、証拠のない試行を成功と報告しません。localとcloudは同じcoreです。\n\n## 現在地\n\nrepositoryとTelegram入口は公開されています。local / cloud componentと複数の専門loopはrepositoryに存在します。user数、revenue、retention、銀行口座の完全接続、投資成績、demo、founder videoは、最新証拠を検証するまで外部claimにしません。\n\n## Business model\n\nlocal self-hostはfree、常時稼働cloudをsubscriptionにする計画です。金融成果連動feeは法務、risk、user同意を別途検証するまで現行claimにしません。\n\n## 導線\n\n- Product: ${productUrl}\n- Repository: ${repositoryUrl}\n- Telegram: ${telegramUrl}\n`,
    "deck.md": `${head}\n# ${product} deck source\n\n## 1 — Life Manager\n\nA personal manager for your body, mind, and money.\n\n## 2 — Problem\n\nPeople know what would improve their lives, but action stops between disconnected calendars, forms, health routines, and financial accounts.\n\n## 3 — Product\n\nOne manager coordinates specialist organs, executes within delegated boundaries, verifies the result, and reports in Telegram.\n\n## 4 — Daily Organ\n\nCalendar, event and accelerator applications, job applications, priorities, and follow-through.\n\n## 5 — Physical / Mental Organ\n\nRoutines, wellbeing, and continuity of care.\n\n## 6 — Financial Organ\n\nNet worth, cash flow, expense management, income opportunities, and risk-managed investing.\n\n## 7 — Trust architecture\n\nLeast privilege, deterministic money arithmetic, typed state transitions, receipts, and fail-closed reporting.\n\n## 8 — Delivery\n\nStart locally; use the same core in an always-on cloud service; receive one human-readable Telegram experience.\n\n## 9 — Current proof\n\nPublic repository and Telegram entry point. Other traction and performance claims require current evidence before use.\n\n## 10 — Goal\n\nClose the gap between intention and action, prove the system on one real life, then offer the same core to more users.\n\n${productUrl}\n${repositoryUrl}\n${telegramUrl}\n`,
    "one-pager.md": `${head}\n# ${product}\n\n${oneLiner}\n\n## The problem\n\nA person's life is split across calendars, applications, health routines, bank accounts, investments, and dashboards. Advice is abundant; dependable execution and verification are scarce.\n\n## The product\n\n${product} coordinates a Daily Organ, a Physical / Mental Organ, and a Financial Organ. It uses specialist agents for semantic work and deterministic code for arithmetic, state, permissions, and receipts. The user gets concise Telegram reports with tappable evidence links.\n\n## The wedge\n\nBegin with one founder's local runtime and measurable real-world outcomes: events registered and added to Calendar, applications submitted and confirmed, expenses classified, net worth reconciled, and risk limits enforced. Move the same core to the cloud after local proof.\n\n## Trust\n\nLeast privilege, owner-separated accounts, no invented success, no guaranteed financial returns, and no external claim without fresh evidence.\n\n## Links\n\n- ${productUrl}\n- ${repositoryUrl}\n- ${telegramUrl}\n`,
  };
}

export async function buildApplicationKit({ context, outputDirectory }) {
  const errors = validateStartupContext(context);
  if (errors.length > 0) throw new Error(`Invalid startup context:\n${errors.join("\n")}`);

  const digest = contextDigest(context);
  const artifacts = markdownArtifacts(context, digest);
  const assets = {
    context_version: context.context_version,
    context_digest: digest,
    assets: [
      { type: "product", status: "verified", url: context.links.product.url },
      { type: "repository", status: "verified", url: context.links.repository.url },
      { type: "telegram", status: "verified", url: context.links.telegram.url },
    ],
    excluded: [
      { type: "dashboard", status: context.links.dashboard.status, reason: context.links.dashboard.evidence },
      { type: "demo_video", status: context.links.demo.status, reason: context.links.demo.evidence },
      { type: "founder_video", status: context.links.founder_video.status, reason: context.links.founder_video.evidence },
    ],
  };
  artifacts["assets.json"] = `${JSON.stringify(assets, null, 2)}\n`;

  for (const [file, content] of Object.entries(artifacts)) {
    const artifactErrors = validatePublicArtifact(content, context);
    if (artifactErrors.length > 0) {
      throw new Error(`${file} failed public artifact validation:\n${artifactErrors.join("\n")}`);
    }
  }

  await mkdir(outputDirectory, { recursive: true });
  for (const [file, content] of Object.entries(artifacts)) {
    await writeFile(resolve(outputDirectory, file), content, "utf8");
  }

  return {
    context_version: context.context_version,
    context_digest: digest,
    files: Object.keys(artifacts).sort(),
  };
}

async function main() {
  const contextPath = new URL("../../.agents/startup-context.json", import.meta.url);
  const outputDirectory = fileURLToPath(new URL("../../fundraising/application-kit/", import.meta.url));
  const context = await loadStartupContext(contextPath);
  const result = await buildApplicationKit({ context, outputDirectory });
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  await main();
}
