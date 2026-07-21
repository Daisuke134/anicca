# Cloud Agent State/Artifact Inventory

## Status and approval boundary

builder-owned
[`cloud-agent-state-artifact-discovery-manifest.json`](./cloud-agent-state-artifact-discovery-manifest.json)は常に`review_required / pending_independent_architecture_review`を保持する。別artifact
[`cloud-agent-state-artifact-discovery-review.json`](./cloud-agent-state-artifact-discovery-review.json)はcanonical manifest digest、parent digest、exact source revision mapへbindし、independent fresh reviewが`approved`とした。approval basisはexact `todo3_independent_candidate_review_approved_v1`、reviewer roleは`independent_fresh_sol_review`である。builder manifest自体はself-approveしない。

通常のcollector/generatorはapproved reviewを検証して成功し、tracked observation、object JSON、全edgeは`independent_review_approved`を持つ。missing、pending、wrong basis、stale manifest/parent/source bindingは引き続きnonzero・stdout 0・output非作成でfail closedする。`--candidate`はpre-review workflow用に残るが、approved reviewをcandidateへdowngradeできない。

## Inputs and content boundary

親集合の唯一のraw identifier sourceは[`cloud-agent-loop-inventory.tsv`](./cloud-agent-loop-inventory.tsv)である。TODO #3 artifactにはraw `inventory_id`、job/account identifierを保存せず、parent metadataから再計算できるdeterministic opaque `loop_ref`だけを使う。joinと330-parent exact coverageはgenerator memory内で再計算する。

collectorが読むのはparent TSV、manifest/review artifact、manifestでallowlistしたsource/configだけである。reviewed sourceはTODO #2の`O_NOFOLLOW`、held directory fd、regular-file `fstat` helperを再利用し、同じverified fdからSHA-256とAST literal/symbol evidenceを得る。runtime artifactはopen/readせず、`lstat`によるexistence、regular-file type、sizeだけを観測する。artifact content、secret、prompt、payload、auth、cookie、raw personal contentは境界外である。

manifest、review、observations、objects、edgesの文字列fieldは再帰的またはschema単位で検証し、raw parent ID、PII/account/job identifier、control、portable absolute/home/parent-relative path、secret assignment、non-digest opaque entropyを拒否する。source/runtime locatorはreviewed repository/home-relative classに限定し、absolute/home shorthandを出力しない。

## Complete category contract

`REQUIRED_ARTIFACT_CATEGORIES`はexactに次の6値である。

- `state`
- `log`
- `media`
- `transcript`
- `cache`
- `output`

330 loopの各categoryにexact 1 `category_coverage` edgeを持つため、coverage matrixは1,980 rowになる。resolutionは`discovered | none_observed | unverified`だけである。`none_observed`はoperational policyまたはsource schema evidenceなしには生成できない。現在はevidence-backed absence claimがないため、unknown cellをすべて`unverified`とし、absenceへ昇格しない。

definitionはcategory coverageと別の330 edgeであり、6-category matrixを満たさない。cross-poster 2 loopの`cache`と`media`だけがreviewed static source evidenceによりreal objectへbindし、残るcategory cellはcategory別shared unverified objectへbindする。earn watcherのstate/output 3 objectはparentがTODO #1に存在しないためcatalog-only `unbound_parent_unverified`を維持する。

object sizeはobject inventory
[`cloud-agent-state-artifact-objects.json`](./cloud-agent-state-artifact-objects.json)に1回だけ置き、edge
[`cloud-agent-state-artifact-inventory.tsv`](./cloud-agent-state-artifact-inventory.tsv)へ複製しない。OpenClaw 222 loopのdefinitionは1 shared-container objectへ222 definition edgeを持つ。個別job fragment sizeは安全に測定していないため記録しない。retention/SSOTはclassificationとevidence kind/locatorの許可tupleを強制し、根拠がなければ`unknown/unverified`である。

## Approved summary

| Measure | Count |
|---|---:|
| Parent / edge / object | 330 / 2,310 / 120 |
| category coverage / definition edge | 1,980 / 330 |
| discovered / unverified category cell | 4 / 1,976 |
| observed / unverified object | 108 / 12 |
| shared OpenClaw object / definition edge | 1 / 222 |
| catalog-only unbound discovery object | 3 |

TODO #3はindependent approvalとfinal semantic gatesの両方を根拠にcompletion判定する。

## Reproduce approved outputs

```bash
python3 scripts/collect-cloud-agent-state-artifact-metadata.py --output /tmp/cloud-agent-state-artifact-a.json
python3 scripts/collect-cloud-agent-state-artifact-metadata.py --output /tmp/cloud-agent-state-artifact-b.json
cmp /tmp/cloud-agent-state-artifact-a.json /tmp/cloud-agent-state-artifact-b.json
python3 scripts/generate-cloud-agent-state-artifact-inventory.py \
  --check \
  --observations /tmp/cloud-agent-state-artifact-a.json \
  --output /tmp/cloud-agent-state-artifact-inventory.tsv \
  --objects-output /tmp/cloud-agent-state-artifact-objects.json
cmp /tmp/cloud-agent-state-artifact-inventory.tsv docs/reference/cloud-agent-state-artifact-inventory.tsv
cmp /tmp/cloud-agent-state-artifact-objects.json docs/reference/cloud-agent-state-artifact-objects.json
python3 -m unittest tests.test_cloud_agent_state_artifact_inventory
gitleaks detect --no-git --redact --config .gitleaks-cloud-agent-state-artifact.toml --source docs/reference/cloud-agent-state-artifact-discovery-manifest.json
gitleaks detect --no-git --redact --config .gitleaks-cloud-agent-state-artifact.toml --source docs/reference/cloud-agent-state-artifact-discovery-review.json
gitleaks detect --no-git --redact --config .gitleaks-cloud-agent-state-artifact.toml --source docs/reference/cloud-agent-state-artifact-observations.json
gitleaks detect --no-git --redact --config .gitleaks-cloud-agent-state-artifact.toml --source docs/reference/cloud-agent-state-artifact-objects.json
gitleaks detect --no-git --redact --config .gitleaks-cloud-agent-state-artifact.toml --source docs/reference/cloud-agent-state-artifact-inventory.tsv
gitleaks detect --no-git --redact --config .gitleaks-cloud-agent-state-artifact.toml --source docs/reference/cloud-agent-state-artifact-inventory.md
```
