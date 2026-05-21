# VPS の OpenClaw gateway を一旦停止する

**理由:** ローカルと VPS の両方が Slack に繋がると二重返信になるので、VPS 側は止めておく。

**叩くコマンド（ローカル Mac のターミナルで）:**
```bash
ssh anicca@46.225.70.241 'systemctl --user stop openclaw-gateway.service'
```

何も出ずに戻ってくれば停止済み。

**再開するとき（VPS にログインして）:**
```bash
ssh anicca@46.225.70.241
systemctl --user start openclaw-gateway.service
exit
```
