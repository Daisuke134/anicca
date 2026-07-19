# Verification Architecture: Marketing Session Lifecycle

| Property | Requirement | Verification |
|---|---|---|
| PROP-001 | REQ-001, REQ-002, REQ-009 | rendered prompt assertions: signup-only、browser/warming/started_warming、login/dump 禁止 |
| PROP-002 | REQ-003 | pure day-count unit cases: created=today => 1、yesterday => 2、2日前 => 3 |
| PROP-003 | REQ-004, REQ-005 | fake instagrapi Client: day3 login/feed/dump 各1回、ready/instagrapi |
| PROP-004 | REQ-006 | existing settings/attempt marker cases: password login 0回、dead session は非ready |
| PROP-005 | REQ-007, REQ-008 | goal-monitor stub poster: young/browser は invocation 0、marker なし。aged/instagrapi は invocation 1 |
| PROP-006 | REQ-010 | before/after JSON row count と非対象 row equality |
| PROP-007 | 全件 | shell syntax、py_compile、clip pytest/shell tests、capafy state/provision tests |

Purity boundary: day 計算と account eligibility は pure。Instagram login/feed/dump、filesystem state write、cooked marker は effect boundary。テストは effect boundary を temp HOME と fake executables で置換する。
