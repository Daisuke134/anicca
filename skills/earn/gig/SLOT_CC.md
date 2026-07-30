# earn/gig

`earn/gig` はLife Manager内で独立して毎日動くlocal OSS revenue loop。

## Runtime

| piece | file | role |
|---|---|---|
| CORE | `gig-cli.sh` | tmux supervisor。実passはhost schedulerが起動 |
| PASS | `gig_pass.sh` | 納品、出品、返信、応募の4 lane |
| HEALTHCHECK | `gig-healthcheck.sh` | core/browser/disk/sandboxの監視 |
| AUDITOR | `auditor.sh` | SLO、reality verification、repair queue |
| REPORT | `scripts/telegram_report.py` | 即時、毎時、日次、週次のhourensou |
| MAIN ENTRY | `run.sh` | Life Managerの`earn/gig` slot |

## Money path

売上は接続したmarketplace accountへsettleする。`earnings.jsonl`へ記録するのは、
実画面が検収または支払を示し、外部evidenceがある場合だけ。日常運転にhuman操作を
要求せず、初回KYC/OAuth/credential bootstrapだけを利用者が行う。

## Four revenue lanes

| 順 | lane | canonical evidence |
|---:|---|---|
| 1 | 納品 | artifact、acceptance、talkroom readback |
| 2 | 出品 | seller readback、service ID、listing ledger |
| 3 | 返信 | send ACK、talkroom readback、reply ledger |
| 4 | 応募 | helper ACK、公式応募管理、application ledger |

pass後はfresh funnelを作り、外部best practiceに基づく単一experimentを
minimum sample到達後にkeep/revertする。

## Portable paths

- canonical package: `skills/earn/gig/`
- executor: `runtime/agent-runner/`
- browser: `skills/browser/`
- state/credential/evidence: repo外。Gitへtrackしない

```bash
cd /path/to/life-manager
bash skills/earn/gig/gig-cli.sh
bash skills/earn/gig/monitor.sh
```

host unitの生成・登録はGig installerがtemplateから行う。source plistを直接copyしない。
