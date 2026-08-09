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
| current host | `macOS 15.6 / Apple M4 / 16 GiB / free 32 GiB (35.2 GB)` | Read-only host inventory; control plane only |
| current host OS / architecture | `Darwin / arm64` | Current host is not Windows |
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
| existing GCP config | present; instance count `0` | Not evidence of a Windows worker |

## Route decision

JRA FAQ 436 says Data Lab is Windows-only and unavailable on Mac; FAQ 210 says the macOS JV-Link is unsupported. Developer topic 49 identifies JV-Link as an ActiveX COM control. Microsoft lists 64 GB storage as the Windows 11 minimum and lists Windows 365/Parallels as Mac options; Parallels KB 125343 describes Arm-based guests. Therefore no local internal-disk Windows ARM VM, Wine, or x64 emulation is used or treated as JV-Link support. The required route is Mac control plane plus an owned remote/native Windows 11 x64 provider worker. Windows 365/Parallels remain candidate experiments until a real JRA probe passes.

## Probe decision

HRA-2R1は`BLOCKED`。現在のhostはWindowsではなく、JV-Link/Data Labとvalid service key/entitlementを実行環境で確認できない。公式/upstream probe commandは実行しておらず、provider sessionもreal JRA recordも観測していない。synthetic data、synthetic test、clone、scaffold、scraping、netkeiba、Wine互換実行は使用していない。

`REAL_PROVIDER_RECORD`には昇格しない。`probe_command_exit: null`は未実行を表し、成功を意味しない。

## Required external dependency

次に必要なのは、owned Windows上のJRA-VAN Data Lab/JV-Link installation、valid service key/entitlement、pinned `miyamamoto/jrvltsql` checkout、公式/upstream documentationに記載されたprobe commandである。これらが揃うまでprovider sessionを開始せず、JRA laneをHRA-2Sへ進めない。

Primary sources: [FAQ 436](https://support.jra-van.jp/jravan/detail?site=SVKNEGBV&category=24&id=436), [FAQ 210](https://support.jra-van.jp/jravan/detail?site=SVKNEGBV&category=24&id=210), [developer topic 49](https://developer.jra-van.jp/t/topic/49), [Windows 11 requirements](https://www.microsoft.com/en-us/windows/windows-11-specifications), [Microsoft Mac options](https://support.microsoft.com/en-us/windows/experience/platform-variants/options-for-using-windows-11-with-mac-computers-with-apple-m1-m2-and-m3-chips), [Parallels KB 125343](https://kb.parallels.com/en/125343).

## Resend inquiry truth update

- **status**: `API_ACCEPTED_DELIVERY_UNVERIFIED`
- **recipient**: `office@jra-van.jp`
- **subject**: `JRA-VAN Data Lab / JV-Link 5.0.0 の Windows 365 Cloud PC 対応について`
- **submitted_via**: Official Resend API
- **resend_post_http**: `200`
- **provider_message_id**: `39b44ea4-57f9-4429-84b2-917320d81b40`
- **submission_timestamp**: `unavailable_at_post`
- **verification_get_http**: `401`
- **verification_error**: `restricted_api_key` — `This API key is restricted to only send emails`
- **duplicate_send_count**: `0`
- **reply_received**: `false`

**Truth boundary.** Resend accepted the send request, but delivery/readback is unverified because the configured key cannot call `GET /emails/{id}`.

**Next evidence.** An official written compatibility reply is required.
