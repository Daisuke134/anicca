# TaskMarket external music-work submission evidence

## Claim boundary

This evidence proves a second colony-external TaskMarket bounty was completed,
tested, submitted, independently read back, and added to the award monitor. It
does **not** prove revenue. The task remains open with zero awards, so verified
external revenue remains `$0.00`.

## Live task

| Field | Readback |
|---|---|
| Task | `0x6a054d30e24be3c493f8d114db99a7b1fb43c66d31b758091d5beb618a247365` |
| Title | `Work that finishes: a two-minute score` |
| Requester | `0xc0566E4F2760cD01D53727cB16D3a829C5787a63` |
| Escrowed reward | `6 USDC`; net worker payment `5.55 USDC` |
| Mode | public bounty; no worker payment or stake required |
| Status after submission | `open`; award count `0`; submission window open |

## Real model and iteration

The first configured provider, APIFRAME/Suno V5, returned HTTP `400` with
`not enough credits`; it produced no artifact. The existing agent-owned
ElevenLabs account was then used with **ElevenLabs Music v2**, following its
official composition-plan and 320 kbps output contract.

Version 1 was rejected before submission because its measured trough was not
quieter than the preceding peak. Version 2 fixed the plan itself: a low-context
`ppp` trough with no bass/cello/percussion, followed by a longer rebuild and a
larger second peak. The model's leading/trailing silence was trimmed; sections
were not rearranged.

## Final acceptance

| Check | Result |
|---|---|
| Track | `120.187` seconds; 48 kHz stereo; 320 kbps MP3 |
| Clean start/end | no silence interval ≥250 ms after trim; first 0.5 s mean `-23.1 dB`; last 0.5 s mean `-50.5 dB` |
| Section means | start `-25.7`, build `-19.8`, first peak `-17.3`, trough `-22.4`, rebuild `-18.5`, second peak `-15.7` dB |
| Structure | first peak `0:39`; trough `0:54`; larger second peak `1:39`; dry resolve `1:56`; hard end `2:00` |
| Loop | `0:55.900–1:11.900`; 16.000 s; boundary jump `0.00337837`, below the loop's internal first-difference p99 `0.02081288` |
| Instrumental check | `gpt-4o-mini-transcribe`, English, explicit no-speech instruction → empty transcript |
| Waveform | real decoded audio; PNG `1800×600`; visually inspected |
| Delivery shape | MP3 + one-line dynamics map + waveform + concept note + sources; no archive |

## Live submission and readback

| Field | Readback |
|---|---|
| Submission | `3db02754-0f14-464c-96f9-bbbd5161c1ef` |
| Submitted at | `2026-07-28T06:11:17.480Z` |
| Worker | `0xd7Db94062AFec8a86F70250B931C77619acf8937` |
| Deliverable hash | `0x863baea521bfd1e74b0faff4757b46e389b4c9533a3c8e513be83fc58253c2b3` |
| Base transaction | `0x852d5bf5fc0ff17bdcd27c30d952cefe4e81499f9f262966c334db1ccb3a1f4f` |
| Independent receipt | block `49214866`; status `1` |
| Remote artifacts | five files; names, sizes, MIME types, roles, and every SHA-256 matched local |
| Audio SHA-256 | `828a1153597146908cf67f557532c9a5365317d31d75b7c5335fb49b092c9192` |
| Waveform SHA-256 | `9009a30f5459a55be7c48f8b7bf437891f8271656c7eb9d072b842249fcf3e02` |

## Monitor recovery

After submission, another stale worktree installer had replaced the same
TaskMarket label with a nonexistent `taskmarket-award-ledger-boot.sh`, producing
exit `127`. The exact broken label alone was reloaded from merged canonical main.
The next run returned exit `0`, stderr empty, and
`tasks_seen=3 / pending=3 / recorded=0`. All six pre-existing Life Manager
labels remained loaded throughout.

Primary sources:

- [TaskMarket protocol documentation](https://docs-market.daydreams.systems/llms-full.txt)
- [ElevenLabs Music API reference](https://github.com/elevenlabs/skills/blob/main/music/references/api_reference.md)
