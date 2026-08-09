# NAR provider route and probe evidence

`access_date`: 2026-08-09 Asia/Tokyo
`HRA-2R3 state`: `INQUIRY_FORM_CONFIRMED_REPLY_PENDING` / `ACTIVE/BLOCKED`
`session`: `session0`
`record`: `record0`
`probe`: `null`
`raw_values_exported`: `false`

No provider session, entitlement, provider binary, official sample, or real NAR
record was observed. Public HTML, OSS README claims, synthetic fixtures,
screenshots, DNS/RDAP output, and a form success are route evidence only; they
cannot satisfy the NAR Reality Gate. JRA state remains unchanged.

## Official route decisions

### NAR FAQ — contract inquiry route

- Source: [NAR FAQ](https://www.keiba.go.jp/qa.html), accessed 2026-08-09 Asia/Tokyo.
- Core quote: `レース情報提供に関する契約をご希望の法人・団体等の方は、本ホームページ「ご意見・ご要望」メールフォームから、ご連絡先等付記のうえ当協会までご相談ください。`
- Decision: the linked official form is the correct contract/licensing inquiry route; it is not provider entitlement.

### NAR terms — public HTML boundary

- Source: [NAR terms](https://www.keiba.go.jp/terms.html), accessed 2026-08-09 Asia/Tokyo.
- Core quote: `事前の許諾なく転載、複製することを禁じます。`
- Decision: do not treat public HTML as a licensed bulk dataset or start a race-page crawler.

### NAR robots — no probe paths

- Source: [NAR robots.txt](https://www.keiba.go.jp/robots.txt), accessed 2026-08-09 Asia/Tokyo.
- Observed directives:

```text
Crawl-delay: 10
Disallow: /KeibaWeb/TodayRaceInfo/
Disallow: /KeibaWeb/DataRoom/
Disallow: /KeibaWeb/DataDownload/
```

- Decision: no crawler or probe is run against these paths.

### Old-domain current observation

- Source: DNS lookups for `keiba-data.net`, `www.keiba-data.net`, `umaconn.com`, and `www.umaconn.com`, accessed 2026-08-09 Asia/Tokyo; no A, AAAA, or NS answer was returned.
- Source: [Verisign RDAP UMACONN.COM](https://rdap.verisign.com/com/v1/domain/UMACONN.COM), accessed 2026-08-09 Asia/Tokyo; HTTP 404 observed.
- Source: [GMO RDAP keiba-data.net](https://rdap.gmoregistry.net/rdap/domain/keiba-data.net), accessed 2026-08-09 Asia/Tokyo; response says `keiba-data.net not found`.
- Decision: this records current DNS/RDAP observations only. It does not claim official discontinuation and does not authorize a replacement provider.

## OSS candidates (not provider proof)

- [`takepan/jrvltsql` at pinned SHA `1e625007fbda90b10dbf4c2d78872e660b894a22`](https://github.com/takepan/jrvltsql/tree/1e625007fbda90b10dbf4c2d78872e660b894a22), accessed 2026-08-09 Asia/Tokyo: README claims Windows-only, 32-bit Python, UmaConn/NV-Link, and NAR parsers `HA`, `NU`, and `NC` only.
- The repository `LICENSE` metadata says Apache-2.0, while the README says commercial use requires prior contact. This candidate is not approved until provider entitlement and that commercial-use conflict are resolved in writing.
- [`miyamamoto/nvlink-bridge` at pinned SHA `2d005f853f897d71e9f37981b63ead9e14ee8e84`](https://github.com/miyamamoto/nvlink-bridge/tree/2d005f853f897d71e9f37981b63ead9e14ee8e84), accessed 2026-08-09 Asia/Tokyo: README describes an MIT TCP proxy for a 32-bit Windows COM provider and lists installed UmaConn/NV-Link plus configured service keys as prerequisites.
- A bridge is not entitlement, provider permission, coverage evidence, an official sample, or a NAR record. Neither candidate was installed or run.

## Inquiry evidence

- On 2026-08-09 Asia/Tokyo, Sol submitted once via the [NAR-linked form](https://l-horse.net/anquete/goikengoyoubou), category `その他`.
- The request asked for an active official/licensed machine-readable feed/API/software; racecards, timestamped odds, results/payouts, and paddock coverage where available; current 地方競馬DATA/UmaConn/NV-Link URLs; macOS/Windows 11 x64 requirements and an official sample/probe; eligibility, price, internal prediction/commercial permissions; and automation, retention, derivative-data, and redistribution terms.
- Browser confirmations were exactly `送信が完了しました。` and `送信は正常に完了しました。` No receipt or message ID was supplied; duplicate send count is `0`.
- Sender name and email are intentionally not stored. Telegram milestone message ID: `10040`. The same inquiry must not be resent.

## NAR wait contract

- `target`: written NAR/provider response naming an active official/licensed provider, application URL, supported OS, entitlement/price, machine-use terms, coverage, and official sample/probe.
- `external_reason`: the form warns that individual replies are not guaranteed; no active licensed provider URL is verified.
- `next_check`: 2026-08-12 21:30 Asia/Tokyo.
- `durable_owner`: Sol verifies the reply; Luna performs only resulting environment/edit work.
- `parallel_work`: JRA physical-worker purchase confirmation and JRA-VAN support monitoring; no public NAR scraping or OSS execution.
- If no reply exists at the checkpoint, record `NO_REPLY_OBSERVED` and search an official procurement/licensing contact without changing `record0`.

## Probe gate

The probe remains blocked until written entitlement/provider identity, an owned
supported environment, and an official sample or limited licensed bridge are
verified. No NAR code, provider login, install, network probe, or raw licensed
row is executed in this slice; `probe=null` and `raw_values_exported=false` stay
the source-of-truth state.
