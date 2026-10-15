# Bounded Windows CPython 3.11.9 compatibility check — current C5 precertificate cut

**Result:** Pass for the byte-locked current C5 source cut and the nine-instance mixed seed-42 request. This is a bounded Windows grammar and public API/CLI smoke, not a C5 certificate, frozen archive, full 191-instance check, Linux 3.11 check, or release qualification.

## Locked inputs and isolation

- Worktree: `C:/Users/cl2749/.codex/worktrees/stochastic-schedule-extraction/archetype-atlas`.
- Source cut: `build/task-10/c5-current-source-cut-20261014-02.json`, SHA-256 `c553ccdddfbe45743481775132c8b65df6dda50469a9301b99f3eedd5dd5f430`. The exact listed source bytes, mixed request, and resource manifest matched before copying. Cut 01 was preserved; cut 02 changes release-guide checker text only per its record.
- Input request: `build/task-10/c5-current-mixed-family-request-20261014-01.json`, SHA-256 `cbca123df02b95de45d54c015fc88a358c59cc0b5348bcc753f5bdc0ddd44842`. Explicit schema `1.1.0`, seed 42, 2007 local standard time, six programme instances and three physical fixtures. The 191-instance request was outside this bounded check.
- Compiled resources: `build/task10-restaurant-precert-final-20261014-01-resources`, resource set `resources-98a6b73726765a86b90ed91af7e1dafb7ac15e615c2ac10c7e7eb5fc54e0ad54`; 2,855 entries, 89,177,138 entry bytes plus manifest. The copied manifest and each resource were loaded by the unchanged `ResourceSet.load` from the copied package `atlas_schedules/data` and verified by its manifest checks.
- Own copied snapshot: `build/task-10/python311-c5-current-20261014-01/snapshot`. All 31 package source/schema files, all resource bytes, the request, and all grammar source bytes were SHA-256 locked in `snapshot-locks.json` **before** running. Lock file SHA-256: `068b91ac21345d1edd59a47928700cd465e46f964555936d20ec11c37df057c5`. The grammar source file list and per-file SHA-256 values are there; its count is 194.
- Portable runtime: Windows CPython `3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]`; `build/task-10/python311-grammar/runtime/python.exe`. Retrieved archive `python-3.11.9-embed-amd64.zip`: 11,249,023 bytes; SHA-256 `009d6bf7e3b2ddca3d784fa09f90fe54336d5b60f0e0f305c37f400bf83cfd3b` (rechecked).
- Runtime command used `-I -S` from an empty own working directory with only the copied package added to `sys.path`, no site packages. The execution wrapper blocked network/subprocess audit events and file opens outside the own snapshot/build directory or portable runtime. It did not import repository scripts or monkeypatch `ResourceSet.load`.

## Actual checks

- CPython 3.11.9 `py_compile` compiled all **194/194** current repository `.py` files copied from source, including package, scripts and tests; output `.pyc` files went only to `grammar-cache`. Exclusions: build artifacts, Git, `.superpowers`, vendor, runtime, virtual environments and caches. No failures. This checks 3.11 grammar (including f-string rules) without importing nonstdlib test/script dependencies. Grammar result SHA-256: `d7cc63ec713d9e693711b2e83d79acfc6cbd1828fdaf0226ef242a4e62d432f3`.
- The copied public `atlas_schedules.generate(params, seed)` ran on the exact mixed request and copied resource set. The unchanged copied `atlas_schedules.__main__.main` then processed the same strict `--request`/`--output` wrapper. Both passed `contract.validate_bundle`, including typed owner, schedule/binding, service-link and nested generated-reference closure.
- API and CLI each emitted **93 schedules, 95 bindings** (53 load, 42 control), with 12 constituents: eight programme (six requested programmes plus two expanded Warehouse source members), three physical-service, and one derived mixture. The original nine instance keys are present; the three physical identities remain distinct. One source composition and one mixed derived result are present.
- `comparison.compare_bundles(api, cli, api["metadata"]["comparison_policy"])` returned **zero scientific differences**, using the source policy’s exact decision/reference checks and named numerical tolerances. The two canonical output SHA-256 values happened to match (`cf69a11dd094d750e25f7abb5e807d2bb46ffa5af13acf580a7a71f0e0e656b2`); JSON byte equality was not used as the numerical acceptance gate.
- Strict CLI negative controls rejected both an envelope version mismatch (`invalid_contract` at `/schema_version`) and a missing seed (`invalid_contract` at `/`), with no output file.

## Reproduction and evidence

- Snapshot command: `python build/task-10/python311-c5-current-20261014-01/snapshot.py`.
- Grammar command: `build/task-10/python311-grammar/runtime/python.exe -I -S build/task-10/python311-c5-current-20261014-01/grammar_check.py`.
- Runtime command: from `build/task-10/python311-c5-current-20261014-01/empty-cwd`, run the absolute portable `python.exe -I -S` with the absolute `runtime_check.py` path. The same invocation of `negative_cli.py` ran the two invalid-wrapper checks.
- Detailed evidence: `snapshot-locks.json`, `grammar-result.json`, `runtime-summary.json`, `negative-cli-summary.json`, `api-bundle.json`, and `cli-bundle.json` in the own build directory. The runtime summary SHA-256 is `019779745dfd040d8dc3caab60a0f5e8687af82b631b8119b0b127545774a59f`.

## Limits

This uses a copied current precertificate cut, so subsequent live source edits are outside the locked sample. It does not assert frozen C5 archive status, C5 certification, current full-suite status, full 191-instance generation, Linux behavior, or native reference parity. The bounded actual 3.11 API/CLI outputs and comparison are valid only for the exact locked request/resources/source stated above.
