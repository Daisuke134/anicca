# Cloud Agent Credential Inventory

## Purpose and SSOT

TODO #2 のloop dependency edge artifactは [`cloud-agent-credential-inventory.tsv`](./cloud-agent-credential-inventory.tsv)、unique credential/finding object artifactは [`cloud-agent-credential-objects.json`](./cloud-agent-credential-objects.json) である。親集合は [`cloud-agent-loop-inventory.tsv`](./cloud-agent-loop-inventory.tsv) の392 `inventory_id` とexact matchする。live非秘密metadataは [`cloud-agent-credential-observations.json`](./cloud-agent-credential-observations.json)、builder candidate manifestは [`cloud-agent-credential-review-manifest.json`](./cloud-agent-credential-review-manifest.json)、分離したindependent review artifactは [`cloud-agent-credential-rebind-review.json`](./cloud-agent-credential-rebind-review.json) である。builder manifestとindependent artifactは現在pendingであり、独立review後に独立artifactだけが `approved / todo2_392_rebind_independent_review_approved_v1 / independent_fresh_credential_reviewer` へ遷移できる。independent artifactはbuilder manifest、ordered parent、observation、object、inventoryの5 digestへexact bindする。generator normal modeはこのexact approvalがない限りfail closedし、current candidateの検証にはexplicit `--candidate`を要求する。

TSV列は `loop_dependency_edge_id`, `inventory_id`, `loop_state`, `dependency_status`, `credential_object_id`, `consumer_locator`, 実操作分類の `permission_scope`, `dependency_basis`, `evidence_locator`, `parent_metadata_digest`, `source_revision_digest`, `config_revision_digest` である。provider/account/ref/policyはunique object側だけに置き、edgeはobject IDを参照する。

- `observed`: 安全なreference nameとprovider routeを確認した。
- `none_observed`: 完全に検査できたconsumerにcredential referenceが無い。
- `unverified`: parse error、opaque input、未構成agent、帰属不能finding、または検査不能。absenceを意味しない。
- `policy_violation`: reachable subscription OAuthまたはplaintext credentialを検出した。除去はTODO #28。
- `inactive`: verifiedなlive cron metadataとreview provenanceでdisabledを確認し、active credential dependencyとして数えない。

## Safety boundary

collectorは公式OpenClaw metadata CLIだけを実行する。cron metadataは固定argvのGateway `cron.list` 2ページをproducerとし、そのstdoutをshellなしで固定jq allowlistへ直接pipeする。親collectorはprompt/payloadを含むraw stdoutをcaptureせず、安全投影だけを受け取る。完全なlistに存在せず、Gateway `cron.get` の固定jq projectionが明示的な構造化 `NOT_FOUND` codeを返した親だけは、`job_id/result/list_complete/individual_get/gateway_revision_digest/observed_at` からなるportable absence evidenceを残す。timeout、auth、gateway、parse、非構造化failureはnot-foundへ変換せず `unverified` にする。artifactへ残すprofile locatorはSHA-256短縮aliasだけで、profile ID、email、secret field value、raw home pathを残さない。collector自身は `.env`、`*.env`、`.env.*`、`openclaw.json`、auth store、cron jobs、prompt、payload、cookie、logを直接open/hashしない。`--probe` と `--allow-exec` は拒否する。

OpenClawのconsumer routeは `agents list`、`models status`、`models auth list` のsafe projectionと、installed version/config schema digestに結び付く。OpenClawはproviderではない。primary/fallbackでreachableな実providerだけを列挙する。新しいOpenClaw親はreview manifestの親exact mapへ明示追加されるまでgenerationがfail closedする。

親metadata、source revision、safe config projectionの3 digestを全rowに記録する。digestは同値比較可能な `sha256:` + 8桁hex×8チャンク表現とし、secret scannerが連続高entropy tokenとして誤認しない。repositoryはstart sourceからTypeScript 5.5.4 Compiler APIの`Program` / `TypeChecker`でstatic/dynamic relative import graphだけを辿る。direct property、literal bracket、`process` / `process.env` の再帰的destructuring、destructured parameter、宣言後代入、env / helper alias、条件式、高階helper引数・戻り値、anonymous callback、object/constructor argumentをlexical symbol identityとfixpointで解決し、path/blob/line/symbolへ結び付ける。shadowingは別symbolとして分離し、到達する再代入、computed/rest process binding、解決不能なcomputed/alias read、constant-foldできないlocal `require()` / `import()`、またはliteral relative importのmissing target・unsupported extension・symlink・replacement raceはfail closedする。ENVIRONMENT provenanceをunknown/imported/mixed calleeへ渡しcalleeを完全解決できないcallもfail closedするが、ENVIRONMENTを渡さないunknown callとcredentialに無関係な再帰は未解決envへ昇格しない。代入/deleteだけはcredential consumptionから除外する。`src/generated/prisma` はmachine-generated dependency boundaryとしてfirst-party import graph inspectionから除外し、Prisma runtime内の汎用dynamic environment処理をconsumer credential occurrenceへ混ぜない。同一credentialを複数箇所で読む場合、observationは全occurrenceを保持し、review/object/edgeはlexical-minimum locatorに結び付くunique 1件とする。reviewのcredential ref集合、evidence locator、consumer、scope、canonical object IDはobservationから導出した集合とexact一致しなければgenerationを拒否する。

AST parserはcurrent worktree内のGit追跡対象である専用最小package `tools/credential-ast-parser` だけを使用する。`package.json` とlockfile v3はTypeScript `5.5.4` exact pinおよびnpm SHA-512 integrityを持ち、collectorはtool directory、package.json、package-lock.json、installed package.json、`lib/typescript.js`を含む全path componentをread前に`lstat`し、current worktree内の非symlink regular file/directoryであることを確認する。その後にinstalled package versionと `lib/typescript.js` SHA-256 `f7ff3e27aafe5dcc82d0307575e9a7dc5b053b141da123bec81c858537765b56` を独立検証する。execution時はtrusted repository root dir fdをanchorに、parser、projector、sourceの全ancestorとleafを`openat(dir_fd)` + `O_NOFOLLOW`でwalkする。Nodeは継承fdからTypeScript/projector/sourceを読み、source blob OIDも同じ保持source fdのbytesから導出するため、projection後にsource pathを再openしない。ancestor symlink/replacement、worktree外fallback、wrong version/integrity/artifact、未配置はfail closedし、collection中にinstallやnetwork取得を行わない。専用installは約21MBであり、landing全依存約317MBを複製しない。

credential object validatorはcredential typeをclosed enumへ制限し、noncanonical OAuth/plaintext aliasを拒否する。evidence locatorはrepository、OpenClaw safe projection、launchd typed portable componentのfull grammarだけを許可し、その他のstring fieldはprefix/boundary位置を含むraw absolute/home/volume/drive/UNC pathを拒否する。subscription OAuthとplaintext credentialはcanonical auth kindからそれぞれexact `policy_violation` / basis tupleを要求し、plaintext objectは対応findingなしでは生成できない。gitleaksはdefault ruleに加えて全string fieldの既知prefixなしhigh-entropy tokenを検査し、artifact用chunked digest、blob digest、UUID、canonical object IDだけをsecret group単位で除外する。

LaunchAgent sourceは全argvから安全に投影したwrapper/executable/config componentをまとめてblob固定するが、env-like componentはhashしない。LaunchAgent configはraw plistをhashせず、`plutil` producerから固定jqへ直接pipeした `schema_version/program/working_directory/argument_count/paths` のみをcanonical digest化し、`EnvironmentVariables` 値を親processへcaptureしない。Homebrew/package-manager componentは再取得可能な明示 `system:/opt/homebrew/...` locatorとlive blobを持つ。取得不能またはreference graph未検査なら `none_observed` / `references` を許可せず `unverified` へfail closedする。live observationsとreview manifestのいずれかが変わればgeneratorはstaleness errorで停止する。

## Measured inventory

| Measure | Count |
|---|---:|
| Parent loops covered | 392 / 392 |
| Loop dependency edges | 396 |
| Unique credential objects | 18 |
| Loop-used credential objects | 10 |
| Catalog-only credential objects | 8 |
| Unique unattributed finding objects | 1 |
| `observed` edges | 10 |
| `none_observed` edges | 35 |
| `inactive` edges | 0 |
| `unverified` edges | 351 |
| `policy_violation` edges | 0 |
| Source revision unverified parents | 31 |
| OpenClaw audit plaintext findings | 39 |
| OpenClaw audit unresolved refs | 0 |
| OpenClaw audit legacy residue | 6 |

OpenClaw親222件のうちlive cron metadataは217件、親inventoryにだけ残る5件はsafe retryでstderr class `unstructured_not_found` となる。これは明示的な構造化Gateway `NOT_FOUND` responseではないためabsence objectは0件で、5件は `cron_metadata_unavailable` / `unverified` のままである。過去のabsenceを保持・完了根拠にしない。今回のlive収集ではOpenClaw schema digestとaudit finding countが旧334-parent approvalから変化したため、旧OpenClaw decisionを流用せず222件すべてを独立review待ちの`unverified`へ戻す。18 credential objectのうち10件はloop edgeから参照され、8件はcatalog-onlyである。unattributed plaintext findingは1つのconfig-level finding objectとして保持し、各loopへ複製しない。この392-parent値はcandidateであり、TODO #2の完了値ではない。

`openclaw_revision` はexact `version_digest/schema_digest` schemaを持ち、source locatorのversion identityとschema digestからgateway/source revisionを独立導出して全OpenClaw親とcron failure/absenceへexact bindingする。cron failure/absenceはtop-level map、親observation、review recordの6 field tupleとID集合をexact一致させる。`dynamic_openclaw` はverifiedなversion/schema/source/config、job-specific safe cron metadata、`inspection_status=verified` が揃う場合だけ許可し、observed/policy edgeはlive `enabled=true` / `payload_kind=agentTurn` とreview済みderived referenceのkind/object/locatorへexact bindingする。inactive edgeも同じrevision/inspection/review provenanceを要求する。いずれかが欠ける親はstateに関係なく `unverified` edgeだけを許可する。

source revisionがunverifiedの31親はreview decisionと生成edgeを `unverified` に保ち、`none` / `references` / `none_observed`へ昇格しない。

fresh収集でsource revisionが変化したLaunchAgentは旧 `none` reviewを再利用せず `source_revision_changed_review_required` / `unverified` に戻す。

Historical iteration 14 snapshotでは、実在しないliteral relative runtime importを持つ単一repository親をsilent skipせずreference inspection `unverified`へ戻し、330親 / 456 edge / 55 credential object / 1 findingを記録する。このhistorical countはcurrent candidate countではない。

## Reproduce and verify

```bash
npm ci --ignore-scripts --no-audit --no-fund --prefix tools/credential-ast-parser
python3 -m py_compile scripts/collect-cloud-agent-credential-metadata.py scripts/generate-cloud-agent-credential-inventory.py tests/test_cloud_agent_credential_inventory.py
python3 -m unittest tests.test_cloud_agent_credential_inventory -v
python3 scripts/collect-cloud-agent-credential-metadata.py --parent docs/reference/cloud-agent-loop-inventory.tsv --output /tmp/cloud-agent-credential-observations.json
diff -u <(jq 'walk(if type=="object" and has("observed_at") then .observed_at="<observed_at>" else . end)' docs/reference/cloud-agent-credential-observations.json) <(jq 'walk(if type=="object" and has("observed_at") then .observed_at="<observed_at>" else . end)' /tmp/cloud-agent-credential-observations.json)
python3 scripts/generate-cloud-agent-credential-inventory.py --check --candidate > /tmp/cloud-agent-credential-inventory.tsv
cmp /tmp/cloud-agent-credential-inventory.tsv docs/reference/cloud-agent-credential-inventory.tsv
python3 -m trace --count --missing --summary --coverdir /tmp/cloud-agent-todo2-trace --module unittest tests.test_cloud_agent_credential_inventory
artifact_gate=$(mktemp -d)
cp docs/reference/cloud-agent-credential-observations.json docs/reference/cloud-agent-credential-review-manifest.json docs/reference/cloud-agent-credential-rebind-review.json docs/reference/cloud-agent-credential-objects.json docs/reference/cloud-agent-credential-inventory.tsv "$artifact_gate"/
gitleaks dir "$artifact_gate" --config .gitleaks-cloud-agent.toml --redact --no-banner
```

OpenClaw公式は `models auth list` をsecretをdumpしないinspectionとして案内する: https://github.com/openclaw/openclaw/blob/main/docs/help/faq-models.md 。SecretRef migration gateは `openclaw secrets audit --check` のcleanを要求する: https://github.com/openclaw/openclaw/blob/main/docs/gateway/secrets.md 。finding enumの正本は `SecretsAuditCode` の4値である: https://github.com/openclaw/openclaw/blob/744a698fc5e03e1f63429b0632f097872d62e6cd/src/secrets/audit.ts 。Gatewayの個別job取得は `cron.get` handlerである: https://github.com/openclaw/openclaw/blob/37ac5d671fbcabc7529e2e7f9876c264e86e6c33/src/gateway/server-methods/cron.ts 。runtime auth resolverの正本は `api.runtime.modelAuth.getRuntimeAuthForModel` / `resolveApiKeyForProvider`: https://github.com/openclaw/openclaw/blob/main/docs/plugins/sdk-runtime.md 。

Node.js公式の`child_process` docsはnumeric fdをchildへ継承できることを定義する: https://github.com/nodejs/node/blob/v25.9.0/doc/api/child_process.md 。Node.jsの`fs.readFile`実装はnumeric fdを既存fdとして扱う: https://github.com/nodejs/node/blob/main/lib/fs.js 。

TypeScript公式public APIは `Program.getTypeChecker()` をsemantic analysisの入口、`getSymbolAtLocation` をnodeからsymbolを解決するAPIとして定義する: https://github.com/microsoft/TypeScript/blob/main/src/compiler/types.ts 。npm公式は`npm ci`について「既存package-lockが必須でinstallはfrozen」と説明する: https://github.com/npm/cli/blob/latest/docs/lib/content/commands/npm-ci.md 。package-lockはexact treeを記述し、`integrity` は展開artifactのSubresource Integrity文字列である: https://github.com/npm/cli/blob/latest/docs/lib/content/configuring-npm/package-lock-json.md 。
