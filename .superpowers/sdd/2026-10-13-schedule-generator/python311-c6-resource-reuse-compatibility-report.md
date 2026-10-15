# C6 post-R26 bounded actual Windows Python 3.11.9 verification

**Status: PASS for this exact cut and mixed request.** The current private resource-reuse path and public source-composition path worked under actual Windows CPython 3.11.9. Wrong private resource type/RID and independently corrupted public resources were rejected. The three scientific comparisons had zero differences. This is a bounded precertificate result, not a full 261-case, complete test-suite, frozen archive, Linux, or native-method certification.

## Inputs, copies, and isolation

- Worktree: `C:/Users/cl2749/.codex/worktrees/stochastic-schedule-extraction/archetype-atlas`. All generated evidence is under `build/task-10/python311-c6-resource-reuse-20261015-01` (the ownbuild root). The fixed report is this file. No source, schema, test, Git, index, or branch mutation occurred.
- Post-R26 source cut: `build/task-10/c6-stable-source-cut-20261015-02.json`, SHA-256 `f6997ac529dfe43eefa5a17f97989d7ebe853caa2993af1266a0f6a1138c3034`, recorded Git HEAD `f7c165741c97f5d2b9e8caef5f631a2cca725ad1`. Before copying and after the checks, all **210** raw Python and **32** package runtime/schema hashes matched the live cut. All copied hashes matched afterward. All **44** implementation fingerprints matched after CRLF-to-LF normalization. Final lock results are in `final-locks-summary.json`.
- Copied source/resource/request locks: `snapshot-locks.json`, SHA-256 `5b82eb9b1859cb999155001b13a4fbffaddda24e46f78698e29e07c3658ac3d1`. Exactly 3,458 manifest resource entries (96,971,639 entry bytes) plus manifest were copied under `snapshot/atlas_schedules/data`. The resource ID is `resources-f99ad2b53ea4b7d07790fcce53c6ea7546fff90ae529f23ac6e9dd7aa578e15f`; copied and live manifest SHA-256 is `f2e59b4f4fbbe3cc5438ccb6cf1f89a35c822133e151e05356acdf1f9410a766`. The copied `ResourceSet` checked its complete inventory, byte lengths, hashes, and ID in the successful runtime children.
- Mixed request: `build/task-10/c6-current-precert-20261015-01/mixed-family-request.json`, copied byte-for-byte as `mixed-request.json`, SHA-256 `cc50100db00a648b6dd44a5cb225602b27ea2b6842342fa397465aca78901cf9`. It has schema 1.1.0, seed 42, calendar year 2007 in local standard time, seven programme and four physical-service requested instances.
- Pinned interpreter: `build/task-10/python311-grammar/runtime/python.exe`, version `3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]`. Existing official archive `build/task-10/python311-grammar/python-3.11.9-embed-amd64.zip` was rechecked at SHA-256 `009d6bf7e3b2ddca3d784fa09f90fe54336d5b60f0e0f305c37f400bf83cfd3b`; no download. The baseline was `C:/Python314/python.exe`, version 3.14.7.
- `X:` was temporarily mapped to the ownbuild directory via `subst` to keep Windows file paths usable. Copied runtime imports used the Windows extended-path prefix (`//?/X:/snapshot`) because the ownbuild path plus a long resource filename exceeds the usual path limit. That changes only the test harness path spelling, not package source or resource bytes. Each generation/resource child ran `-I -S` from own `empty-cwd` with an audit hook denying network, subprocess, and opens outside the ownbuild or interpreter runtime. The comparisons and CLI-negative child had the same restrictions. Trusted setup/lock inspection read the source cut before the runtime audit. Children ran sequentially.

## Grammar and inherited native-codec evidence

Actual 3.11.9 `py_compile` accepted **210/210** copied Python files, including scripts and tests, with explicit `.pyc` targets under own `grammar-cache`. `grammar-result.json` records the complete file list and zero failures; this is grammar verification for copied files, not import execution of every module.

The prior actual-3.11 XZ-decoder proof is **inherited**, not rerun. Its raw report `python311-c6-current-compatibility-report.md` has required SHA-256 `9933900750ad058d22ef91ed4ea628d29494a67df9f65b28282345e0bfe54a69`. `identity-summary.json` checks exact bytes against its `snapshot-locks.json` for `scripts/schedule_generator_native_codec.py`, `atlas_schedules/canonical.py`, `errors.py`, `resources.py`, the source lock and both containers. The source lock and packaged `reference/retail-programme-native-lock.json` also have identical bytes and SHA-256 `b904788cc2880b0813cc703b30ae277b12a8ebace3939b704dfbbad285a2337c`. Both `new_codec` lock entries match the prior cut, including compressed and decompressed SHA/size receipts:

| Entry | Compressed bytes / SHA-256 | Raw bytes / SHA-256 |
| --- | --- | --- |
| inputs | 117,896 / `8c609d95865bb7c5420ea12405396e757552dab67f3df0ed0ef8743689a0747e` | 30,192,243 / `44448a9c7a8af495ec943f6a72fb69ca161478cf3023a772c2d745b3eaac5ebd` |
| vectors | 1,485,628 / `e048d706c36078b39155f09d50cc5c16536c50f15a63ddfcaa456817c6417c1e` | 330,945,239 / `68e1a129c138c512b5d8153d2ec523f3eda07d4851a1936823e6b3b7178cb3ac` |

The inherited prior actual-3.11 run parsed **336 distinct cases with `source_context` in each entry** for each container, and rejected missing/unknown format and changed-body/hash negatives. Its synthetic legacy-gzip checks remain synthetic; no historical original gzip decode is claimed. Earlier codec summary SHA-256 values are `4dbca581d71dda4096c21ad18567dd7177564163f4c9a2ae4725b799f162cfb2` (inputs) and `00c3329aeea033e7487e1ff1114f22b0e4f31a5783173620baaa4423c8158535` (vectors).

## Generation and scientific comparison

All three children exited **0** on the same copied source, resources, and request: 3.14 API `19.332` s, 3.11 API `30.654` s, 3.11 unchanged CLI `24.624` s. Each output passed `validate_bundle` and had **18** constituents (13 programme, four distinct physical service, one derived result), **123** schedules, **125** bindings (63 load, 62 control), and two source parents (Warehouse C4 and Retail C6). Every requested instance appeared; each schedule had 8,760 values in the requested calendar. The 3.14 canonical output SHA-256 is `25e4faab3a4541b13cd53f31e73738e898ee0d356d9c33edf0d4e81bffcebbda`; both 3.11 API and CLI output SHA-256 values are `eeb421076e7ebc03fe77746cdfb8ef9e1575ae8f4c433fbd87e411fe3434d4ae`.

The copied scientific comparator and declared comparison policy reported **zero differences** in 3.11 API versus 3.14 API (`7.633` s), 3.11 CLI versus 3.14 API (`7.155` s), and 3.11 CLI versus 3.11 API (`7.163` s). Cross-version byte differences were not used as floating-proof failures. The comparator covers source/owner/reference decisions, discrete and RNG receipts, target totals, controls, and hourly trajectories under the named policy. Machine results are `api_vs_314-comparison.json`, `cli_vs_314-comparison.json`, and `cli_vs_api-comparison.json`.

## Resource reuse, authority, and rejection checks

The genuine 3.11 bundle passed validation before mutations. The copied Retail C6 child members were projected into a local valid input, then the private `_compose_constituents` path with an actually verified `ResourceSet` succeeded (`2.035` s), as did the public `compose_constituents` path without an injected snapshot (`5.102` s). Both produced five constituents. The private path rejected `object()` as the wrong snapshot type immediately and a verified `ResourceSet` whose RID was changed to a foreign ID with `resource_integrity` at `/resource_set_id`. In an independent copied package, one byte of the copied `reference/catalogue-index.json` was changed; the public source-composition call rejected it as `resource_integrity` at that resource path (`2.707` s). The locked primary snapshot was never corrupted. Results are `valid-resource-reuse-summary.json` and `corrupt-resource-reuse-summary.json`.

Starting from the same genuine baseline, retargeting the FullServiceRestaurant Main alias coherently to an existing Booster binding, dropping one/all required aliases, and removing the independent inventory were all rejected (`requires_binding`, `requires_binding`, `requires_binding`, `invalid_contract`). Both Warehouse C4 and Retail C6 nested source-parent components were changed to valid in-range binding indices owned by the other parent while retaining their owner/schedule fields; both were rejected as `invalid_reference`. The exact paths and timings are in `authority-negative-summary.json`. The 3.11 CLI rejected a version mismatch and absent seed as `invalid_contract`, with no output created (`negative-cli-summary.json`). These children exited **0** after asserting expected rejection.

## Reproduction commands and limits

The following commands ran from own `empty-cwd` after the trusted `python X:/snapshot.py` copy and `python X:/identity_check.py` identity checks (all completed with exit 0). `X:` mapped to the ownbuild directory. A second copied snapshot was made for the single-byte corruption check. Every command below exited 0:

```text
<pinned-3.11-python.exe> -I -S X:/grammar_check.py
C:/Python314/python.exe -I -S X:/mixed_run.py baseline314
<pinned-3.11-python.exe> -I -S X:/mixed_run.py api311
<pinned-3.11-python.exe> -I -S X:/mixed_run.py cli311
<pinned-3.11-python.exe> -I -S X:/compare_bundles.py api_vs_314
<pinned-3.11-python.exe> -I -S X:/compare_bundles.py cli_vs_314
<pinned-3.11-python.exe> -I -S X:/compare_bundles.py cli_vs_api
<pinned-3.11-python.exe> -I -S X:/authority_negative.py
<pinned-3.11-python.exe> -I -S X:/negative_cli.py
<pinned-3.11-python.exe> -I -S X:/resource_reuse_check.py valid
<pinned-3.11-python.exe> -I -S X:/resource_reuse_check.py corrupt
python X:/final_locks.py
```

`<pinned-3.11-python.exe>` expands to `C:/Users/cl2749/.codex/worktrees/stochastic-schedule-extraction/archetype-atlas/build/task-10/python311-grammar/runtime/python.exe`. The source copy, prior-proof identity, and final lock checks also exited 0. The raw evidence and machine summaries are in the ownbuild root; this report does not claim a fresh native decode, full request, current certificate, frozen archive, full test suite, Linux verification, or new native-reference qualification.

## Temporary X: drive cleanup receipt (2026-10-15)

Before creating the mapping, a `Get-PSDrive -PSProvider FileSystem` inventory returned C:, D:, R:, Temp:, Y:, and Z:, with no X: entry; the adjacent `subst` inventory showed no substitution output. This records X: as absent from those pre-run inventories, although no separate `Get-PSDrive -Name X` query was made at that moment. The verifier then mapped X: to the exact ownbuild target `C:\Users\cl2749\.codex\worktrees\stochastic-schedule-extraction\archetype-atlas\build\task-10\python311-c6-resource-reuse-20261015-01` and used it for the copied proof. At completion, `subst X: /D` exited 0. A subsequent `subst` inventory and `Get-PSDrive -Name X -ErrorAction SilentlyContinue` returned no mapping/drive entry. No further mapping was removed or modified. The pre-append raw report bytes were copied to `build/task-10/python311-c6-resource-reuse-20261015-01/report-before-x-drive-cleanup-note.md`, SHA-256 `d6ea5966af7cc6ab362ad729c02528dd65047516a10440700b18b680ff45ed19`.