# Bounded Windows CPython 3.11.9 compatibility — C5 post-authority fix

**Result:** Pass for the exact current C5 post-authority-fix precertificate source cut, copied resource set, and genuine nine-instance mixed request. This is bounded Windows 3.11 grammar, public API/CLI, and emitted-bundle authority behavior evidence. It is not C5 certification or release qualification.

## Locked snapshot

- Worktree: `C:/Users/cl2749/.codex/worktrees/stochastic-schedule-extraction/archetype-atlas`.
- Cut: `build/task-10/c5-current-source-cut-20261014-03.json`, SHA-256 `c4fd55bebdf934fd7ba373f222b20b68950c8b2f3062036383973901d9508c6b`. The exact listed source bytes, request and resource manifest matched before copying. Cut 02 and its earlier proof remain separate pre-fix evidence.
- Cut 03 records five changed implementation entries versus cut 02: `atlas_schedules/generator.py`, `mixtures.py`, `owners.py`, `services.py`, and the packaged `schedule-generator-bundle-v1_1.schema.json`. The writer reports a matching canonical schema mirror; this bounded proof byte-checked the packaged JSON schema and compiled 194 copied Python files, but did not independently byte-check the canonical mirror. No resource/native/RNG/target changes were asserted by this compatibility check.
- Request: `build/task-10/c5-current-mixed-family-request-20261014-01.json`, SHA-256 `cbca123df02b95de45d54c015fc88a358c59cc0b5348bcc753f5bdc0ddd44842`; schema 1.1.0, seed 42, 2007 local standard time, six programme and three physical-service instances.
- Resource root: `build/task10-restaurant-precert-final-20261014-01-resources`; resource ID `resources-98a6b73726765a86b90ed91af7e1dafb7ac15e615c2ac10c7e7eb5fc54e0ad54`; manifest SHA-256 `3a374e683a5678782d7a7c4d3f8690c6e5865160c428a98429111ddb11f77c99`. The copied package contains 2,855 resource entries with 89,177,138 entry bytes, plus the manifest. Unmodified `ResourceSet.load` read that copied package `data` directory and checked its whole manifest inventory.
- Own snapshot/build: `build/task-10/python311-c5-postfix-20261014-01`. `snapshot-locks.json` contains all copied byte SHA-256 values: 194 grammar `.py` files, 31 package files, 2,855 resources plus manifest, and request. Its SHA-256 is `6fd35e68205230a94ee3666936d712bc9da0b9c8375065084a8bfd96cfcc7734`. These bytes were locked before execution; subsequent live edits are outside this sample.
- Runtime: official portable Windows CPython `3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]`, executable `build/task-10/python311-grammar/runtime/python.exe`; source archive 11,249,023 bytes and rechecked SHA-256 `009d6bf7e3b2ddca3d784fa09f90fe54336d5b60f0e0f305c37f400bf83cfd3b`.

## Actual 3.11 checks

- `-I -S` CPython 3.11.9 compiled **194/194** copied repository Python files with `py_compile` and explicit own `grammar-cache` destinations; zero syntax failures. The file list, individual hashes and result SHA-256 (`d7cc63ec713d9e693711b2e83d79acfc6cbd1828fdaf0226ef242a4e62d432f3`) are in the build evidence. Grammar coverage includes package, tests and scripts; build, Git, `.superpowers`, vendor, runtimes, virtual environments and caches were excluded. Nonstdlib test/script imports were not exercised.
- From an empty own working directory and copied package only, actual `atlas_schedules.generate(params, seed)` and unchanged copied `atlas_schedules.__main__.main --request ... --output ...` ran the exact schema/seed/request. Wrapper audit blocked network, subprocess and file opens outside the own build or portable runtime. No repository script import, external package, or `ResourceSet.load` monkeypatch was used.
- API runtime: `22.597` seconds; CLI runtime: `24.564` seconds. Each emitted **93 schedules**, **95 bindings** (53 loads, 42 controls), and 12 constituents: 8 programme (including 2 expanded Warehouse source members), 3 physical-service, 1 derived mixture. The original nine instance keys are present, with one source composition and three distinct fixture identities.
- Both outputs passed unchanged `contract.validate_bundle`: schema, typed owner, schedule/binding, service-link, and nested generated-reference closure. `comparison.compare_bundles(api, cli, metadata.comparison_policy)` found **zero scientific differences** under the resource policy’s exact receipt/reference and named numerical tolerance rules. Output SHA-256 happened to match (`6493e6ff8b9e2115cf8a0d0f4084369a029eaa36e9623cf9bef72d9552daa5c3`); byte identity was not the numerical gate.
- Strict CLI controls rejected a mismatched envelope version (`invalid_contract` at `/schema_version`) and missing seed (`invalid_contract` at `/`), leaving no output file.

## Genuine emitted authority negatives

The unmodified, genuinely generated API bundle passed `validate_bundle` **first** (`3.048` seconds). The full-service restaurant has one independently retained original Main required-service entry and one matching alias. The original required inventory and alias evidence were retained while alias fields were coherently redirected to the **existing** Booster fixture and one of its actual load bindings. No old output annotation or invented fixture was used.

- Main → Booster coherent alias: rejected `requires_binding` at the full-service programme `/required_service_links`; the alias no longer covered the original Main source service.
- Delete the one required alias: rejected `requires_binding` at `/required_service_links`.
- Replace the whole required-alias list with `[]`: rejected `requires_binding` at `/required_service_links`. Since this genuine mixed request has one required alias, this and the preceding mutation remove the same sole requirement through distinct edits.
- Remove the original independent required-service inventory: rejected `invalid_contract` at `/constituents/5` by the schema before service-level validation.

All four mutated bundles were rejected on actual 3.11 without regenerating or changing their other source outputs. Exact codes, paths, messages, and timing are in `authority-negative-summary.json` (SHA-256 `e07232d6839e809dd5608e98cbcc579499610591ab3cb6dd508acead298c1551`).

## Commands and evidence

- Snapshot: `python build/task-10/python311-c5-postfix-20261014-01/snapshot.py`.
- Grammar: `build/task-10/python311-grammar/runtime/python.exe -I -S build/task-10/python311-c5-postfix-20261014-01/grammar_check.py`.
- Public API/CLI: from own `empty-cwd`, absolute portable `python.exe -I -S` with absolute `runtime_check.py`. Authority negatives: same invocation with `authority_negative.py`. CLI wrapper negatives: same invocation with `negative_cli.py`.
- Own evidence files: `snapshot-locks.json`, `grammar-result.json`, `runtime-summary.json`, `authority-negative-summary.json`, `negative-cli-summary.json`, `api-bundle.json`, `cli-bundle.json`; runtime summary SHA-256 `92c0ded0d4160a864b5e590ab0fb264de4dd330f16dff2e1eedc27dc53be7ba2`.

## Limits

The result is specific to Windows CPython 3.11.9, the byte-locked precertificate cut 03 and the nine-instance seed-42 request. It does not prove a frozen C5 archive, full 191-instance generation, Linux 3.11 operation, the full test suite, native reference parity, certificate validity, or release readiness. The earlier cut 02 report remains pre-fix evidence.

