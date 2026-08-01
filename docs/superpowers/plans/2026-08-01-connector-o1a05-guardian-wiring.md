# Connector O1A-05 Guardian Wiring Plan

> Status: 実行中。O1A-05だけを扱い、強制停止・Telegram警告・実復旧の証明はO1A-06へ残す。

## 目的

既存Life Manager runtime worker上の`outbound.event.apply`を、既存Guardianと`self-fix.sh`へ接続する。
新しいqueue、worker、tmux loop、独自heartbeatは作らない。

## 実装契約

1. workerの既存`/health`だけを観測する。
2. HTTP 200だけでは成功にしない。`role=worker`、`outbound.event.apply` capability、freshな`last_poll_at`を必須にする。
3. 判定はpure functionに分離し、到達不能、不正JSON、role違い、capability不足、poll staleをRED testで固定する。
4. 異常時は既存`skills/self/self-fix.sh`へ`connector-outbound`として委譲する。
5. 5分ごとの既存launchd方式で起動できるplistとinstallerを追加する。
6. local composeのworker health portをlocalhostへ公開し、Guardianが同じhealth endpointを読む。

## 変更対象

- Create: `apps/life-manager/lib/outbound-guardian.js`
- Create: `apps/life-manager/lib/outbound-guardian.test.js`
- Create: `skills/self/outbound-runtime-healthcheck.sh`
- Create: `skills/self/launchd/ai.anicca.outbound-runtime-healthcheck.plist`
- Create: `skills/self/install-outbound-runtime-healthcheck-launchd.sh`
- Modify: `deploy/local/compose.yaml`
- Modify: `apps/life-manager/package.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

## 検証

- RED: Guardian testがmodule未実装で失敗する。
- GREEN: Guardian unit test、outbound回帰、runtime worker回帰が成功する。
- plistを`plutil -lint`する。
- installerを副作用なしのrender modeで検証する。
- O1A-05完了後にspec、commit hash、fresh test結果を更新しpushする。

