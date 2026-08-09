# HRA-2R1 JRA probe evidence

status: BLOCKED
evidence_class: BLOCKED
source: JRA-VAN JV-Link / JRA-VAN Data Lab
jurisdiction: JRA
provider_session_count: 0
real_jra_record_count: 0
probe_command_exit: null
raw_values_exported: false

## Checks performed

| Check | Result | Evidence boundary |
|---|---|---|
| current host OS | `Darwin` | Current host is not Windows |
| current host architecture | `arm64` | Read-only host inventory |
| owned Windows worker | false | No owned Windows execution target was verified |
| Parallels Desktop app / CLI | absent / absent | Existing VM cannot be observed without a runtime |
| VMware Fusion app / CLI | absent / absent | Existing VM cannot be observed without a runtime |
| UTM app / CLI | absent / absent | Existing VM cannot be observed without a runtime |
| VirtualBox app / CLI | absent / absent | Existing VM cannot be observed without a runtime |
| Wine / QEMU compatibility runtime | absent / absent | No compatibility assumption made |
| SSH config presence | true | Presence only; target, address, user, and secret were not read |
| SSH known-hosts presence | true | Presence only; host entries were not read |
| RDP client configuration presence | false | No RDP target was verified |
| remote Windows endpoint | unknown | Existing SSH context is not evidence of Windows |
| JV-Link/JRA-VAN local app or CLI | absent | Presence-only app/CLI check |
| JRA-VAN/Data Lab provider filenames | none found | Presence-only filename check; no key or env contents read |
| pinned `miyamamoto/jrvltsql` checkout | absent | Only documentation references were present |
| candidate service-key env names | absent | Names checked with boolean presence only |
| candidate entitlement/license env names | absent | Names checked with boolean presence only |

## Probe decision

HRA-2R1は`BLOCKED`。現在のhostはWindowsではなく、JV-Link/Data Labとvalid service key/entitlementを実行環境で確認できない。公式/upstream probe commandは実行しておらず、provider sessionもreal JRA recordも観測していない。synthetic data、synthetic test、clone、scaffold、scraping、netkeiba、Wine互換実行は使用していない。

`REAL_PROVIDER_RECORD`には昇格しない。`probe_command_exit: null`は未実行を表し、成功を意味しない。

## Required external dependency

次に必要なのは、owned Windows上のJRA-VAN Data Lab/JV-Link installation、valid service key/entitlement、pinned `miyamamoto/jrvltsql` checkout、公式/upstream documentationに記載されたprobe commandである。これらが揃うまでprovider sessionを開始せず、JRA laneをHRA-2Sへ進めない。
