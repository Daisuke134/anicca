# launchd control-plane recovery

Mr.botのlaunchd変更は必ず次の入口を使う。

```bash
bin/launchctl-safe preflight
bin/launchctl-safe kickstart gui/$(id -u)/LABEL
~/loops/current/bin/lm-loop apply
```

preflightはUID、username、Directory Services、Aqua manager、manager UID/PID、`gui/$UID`を
read-onlyで確認する。正常時はexit 0、異常時はexit 75で
`~/.local/state/mr-bot/launchd-control-plane-preflight.json`へexact resultを保存する。

exit 75では次を行わない。

- `launchctl bootstrap`、`bootout`、`kickstart`、`load`、`unload`
- plistの書換え、stale lockのraw削除
- `launchd`、`loginwindow`、`opendirectoryd`、WindowServer、LaunchServicesのkill/restart
- Directory Services recordの作成・変更
- PPID 1だけを根拠にしたprocess終了

`141 Reentrancy avoided`またはmanager rc=153は、job故障ではなく操作context故障として扱う。
既存jobの自然tick receiptを別に読み、全loop停止を推定しない。外部GUI appから孤立した操作contextが
確認された場合は、そのapp自身のstale contextだけを終了・再接続する。OS serviceは触らない。

回復後は次を同じcontextで再実行し、すべて成功してから既存labelだけを操作する。

```bash
id -un
dscl . -read "/Users/$(id -un)" UniqueID
launchctl managername
launchctl manageruid
launchctl managerpid
launchctl print "gui/$(id -u)"
bin/launchctl-safe preflight
```

診断receiptに`status=pass`、`mutation_allowed=true`がなければ復旧完了と報告しない。
