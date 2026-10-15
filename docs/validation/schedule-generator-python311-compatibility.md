# Windows CPython 3.11 standalone smoke

On 2026-10-14, the existing workspace-only official Windows AMD64 CPython 3.11.9 embeddable runtime at `build/task-10/python311-grammar/runtime/python.exe` reported `3.11.9 (tags/v3.11.9:de54cf5, Apr 2 2024) [MSC v.1938 64 bit (AMD64)]`. Its retrieval receipt is `build/task-10/python311-grammar/retrieval.json`: `https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip`, SHA-256 `009d6bf7e3b2ddca3d784fa09f90fe54336d5b60f0e0f305c37f400bf83cfd3b`, 11,249,023 bytes. The ZIP's local hash and size matched that receipt. No second runtime was downloaded or installed.

An independent check ran one checkout-independent standalone generation with `python.exe -I -S`, using the immutable `data/generator-releases/v0.3.0/generator.zip`. The generator ZIP matched its manifest SHA-256 `14e066438e4db2aa7efdd95be1073467262a4aadbfb0319a5a8e40e4b0bf8f69` and size 69,340,139 bytes. Only `references/mixed-family-request.json` was extracted from it, after its member SHA-256 `f84011fe58dcf1a52c487e38cd6c839dbbacad85e9724a25dcc80e45a3f86af9` and size 2,742 bytes matched the manifest.

Command: `python.exe -I -S generator.zip --request mixed-family-request.json --output mixed-family-bundle.json` (all paths resolved to the locations above). Exit code was 0. The output parsed as JSON with 49 schedules, each containing 8,760 values, 51 bindings and 3 constituents. Generated output SHA-256 was `f714cb1daf47564455cd7540a1d070bcf1ec1d0de9054dcc5d8eaf95c10790f3`, 11,130,749 bytes. The exact command, interpreter banner and result are in `build/task-10/python311-c2-check/mixed-smoke-log.json`; the driver is `mixed_smoke.py` in the same directory.

This is one actual **Windows CPython 3.11.9** frozen-v0.3.0 CLI smoke. It does not establish Linux 3.11 behavior, full Python 3.11 suite results, current source-tree compatibility, or scientific parity of regenerated values. The C2 source syntax correction and its before/after compilation are being checked separately by the controller/writer.

## Frozen scientific comparison

The already generated Windows 3.11 bundle was compared with the frozen ZIP's `references/mixed-family-bundle.json.gz` using that same ZIP's `atlas_schedules/comparison.py::compare_bundles` and `atlas_schedules/data/reference/comparison-policy.json`. All three archived members matched the release manifest's member hashes and sizes before use. The comparator returned **zero differences**. Its rules check source/discrete/RNG decisions and source target identity exactly, use the named tolerances for generated arithmetic and annual integrals, and ignore only the documented administrative fields (including `rng.python_version`). This establishes scientific equivalence for this mixed request against the shipped frozen reference; it does not rely on generated JSON byte hashes. The bounded comparison log and driver are `build/task-10/python311-c2-check/mixed-compare-log.json` and `compare_mixed.py`.

This comparison resolves the scientific-parity limitation stated in the smoke paragraph above for this single mixed request. The other platform, suite, and current-source limits still apply.

The compact evidence files were copied byte-identically to `build/task-10/python311-c2-check/` for these documentation references. Original execution paths and commands remain exactly recorded in the logs; the copy is not a second execution.

## Frozen C3 v0.4.0

The controller independently reused that same official Windows CPython 3.11.9
runtime for one frozen v0.4.0 mixed request, with `-I -S`. The 72,240,150-byte ZIP
matched SHA-256 `fb60c9231143af220739bb1947d9ff12262548ab5d449ffd5b90376324090531`.
The request, archived reference, comparator and comparison policy each matched
their manifest member hashes before use. Generation exited 0 and emitted 55
schedules of 8,760 values, 57 bindings and four constituents. The ZIP's own
archived comparator returned zero scientific differences. Exact resolved command,
interpreter banner, member hashes and results are in
`build/task-10/python311-c3-check/check-log.json`; the bounded driver is `check.py`.
The fuller receipt is `python311-c3-compatibility-report.md` in the Task 10 scratch
folder. This supersedes the latest-version smoke claim with one actual Windows
3.11 v0.4.0 mixed request. It establishes no Linux/full-suite/current-source result.

## Frozen C4 v0.5.0

The same official Windows CPython3.11.9 runtime generated the frozen v0.5.0 mixed
request once with `-I -S`:66 schedules of8760 values,68 bindings and7 constituents,
exit0. The own archived comparator/policy found zero scientific differences.
ZIP77,307,554bytes SHA256
`ad0021ba53f2cf4df70059f7a34943cabfcab0d7bd26464189617d9e7d8b16ea`
and the four request/reference/comparator/policy members matched manifest hashes
before execution. Compact driver/output/receipt are in
`build/task-10/python311-c4-check/` and `check-log.json`. Actual3.11.9 grammar also
accepted all158 current runtime/script/test Python files. These bounded Windows
checks establish no full3.11 or Linux suite result.

## C4 public-helper patch source check

Actual official Windows CPython3.11.9 with `-I -S` compiled the two changed
runtime modules and the archived-reference regression file, then passed all five
public composer/ownership regression tests in16.526s. The tests use immutable
v0.5.0 archived arrays and current fixed API without temporal regeneration.
Evidence: `build/task-10/c4-fix1-python311-api-green-20261014-01.log`. This is a
bounded current-source syntax/API check, not a new frozen patch mixed run or a
full3.11/Linux suite claim.

## Current C5 source snapshot

Independent actual Windows CPython3.11.9 checked the byte-locked precertificate
source cut02 (`c553ccdddfbe45743481775132c8b65df6dda50469a9301b99f3eedd5dd5f430`)
with resource set
`resources-98a6b73726765a86b90ed91af7e1dafb7ac15e615c2ac10c7e7eb5fc54e0ad54`.
All194copied repository Python files compiled with the actual3.11 interpreter.
The unchanged public API and CLI, running with `-I -S` from an isolated copied
package/data snapshot, each generated93schedules/95bindings/12constituents from
the explicit1.1 nine-instance seed42mixed request. Typed ownership includes eight
programme owners (two are expanded Warehouse members), three physical services
and one derived result. Bundle validation passed and scientific API/CLI comparison
returned zero differences. Invalid envelope version and missing seed controls
rejected without output. Network/subprocess operations and unrelated file access
were blocked; ResourceSet.load was unchanged.

Evidence is in `build/task-10/python311-c5-current-20261014-01/`:
snapshot-locks.json SHA256
`068b91ac21345d1edd59a47928700cd465e46f964555936d20ec11c37df057c5`,
runtime-summary.json SHA256
`019779745dfd040d8dc3caab60a0f5e8687af82b631b8119b0b127545774a59f`.
The mixed request SHA256 is
`cbca123df02b95de45d54c015fc88a358c59cc0b5348bcc753f5bdc0ddd44842`;
the bounded report is python311-c5-current-compatibility-report.md in the Task10
evidence folder. This proves this exact current Windows source/request snapshot,
not a frozen C5 archive, full191-instance run, native parity or full/Linux3.11 suite.


## C5 after original-service-authority correction

The cut02 check above precedes the service-authority correction. A separate actual Windows CPython3.11.9 check copied stable source cut03, SHA256 `c4fd55bebdf934fd7ba373f222b20b68950c8b2f3062036383973901d9508c6b`, unchanged2855resource entries and the same nine-instance seed42request into its own build. All194copied Python grammar files compile. Genuine unpatched API and CLI runs took22.597s and24.564s; each emitted93schedules/95bindings/12owners, passed bundle validation and compared with zero scientific differences.

The positive emitted bundle was validated before mutations. Coherent Main→existing Booster substitution with original inventory/evidence preserved rejected with requires_binding; dropping one/all aliases rejected with requires_binding; removing the independent original requirement inventory rejected by the1.1schema. Invalid CLI version/missing seed controls also rejected. The helper checked copied packaged JSON-schema hashes separately from Python grammar; the writer independently verifies canonical schema mirrors.

Evidence build/task-10/python311-c5-postfix-20261014-01 contains snapshot-locks SHA256 `6fd35e68205230a94ee3666936d712bc9da0b9c8375065084a8bfd96cfcc7734`, runtime-summary SHA256 `92c0ded0d4160a864b5e590ab0fb264de4dd330f16dff2e1eedc27dc53be7ba2` and authority-negative-summary SHA256 `e07232d6839e809dd5608e98cbcc579499610591ab3cb6dd508acead298c1551`. The bounded report python311-c5-postfix-compatibility-report.md has SHA256 `3c8e193acc7ef9e00f276350c0a2b5422c6b948f58ea04f3b820c6fe8fd8faab`. This is exact current-source Windows mixed-request proof, not a frozen archive, full191-case, native or full/Linux3.11 suite claim.


## C6 current source and native codec

A separate actual Windows CPython3.11.9 proof uses byte-locked stable cut
`0773902cfd1868aefcb79612a9bf219188502b8ecb59b913bedf070a9daba346`
and precertificate resource identity
`resources-f99ad2b53ea4b7d07790fcce53c6ea7546fff90ae529f23ac6e9dd7aa578e15f`.
All209copied Python files compile;32runtime/schema files and44normalized
implementation fingerprints match. The actual copied strict decoder checks both
new declared XZ native input/vector containers: compressed and raw hashes/sizes,
336unique source-context cases each, missing/unknown format and altered-body
rejections. It retains unchanged raw source bytes; historical original gzip was
outside this copied cut, with only synthetic legacy guards exercised.

Sequential3.14API,3.11API and unchanged3.11CLI runs of the same eleven-instance
seed42mixed request emit18owners/123schedules/125bindings, including two real
source parents and four physical fixtures. All three scientific comparisons
return zero differences. Genuine positive output validates before coherent
Main-to-Booster, one/all alias deletion, missing independent requirement inventory
and cross-parent nested binding-reference mutations are rejected. Strict CLI
version/seed controls also reject. Raw cross-version JSON hashes differ and are
not the scientific gate.

The exact raw report python311-c6-current-compatibility-report.md in the Task10
evidence folder has SHA256
`9933900750ad058d22ef91ed4ea628d29494a67df9f65b28282345e0bfe54a69`.
Evidence lives under build/task-10/python311-c6-20261015-01; snapshot-locks SHA256
is `ab1b32f27e4203e0ed73991ecd1b30f2e895c62d2fa5871760e58587a7c1eb99`.
This bounds current-source Windows grammar, codec and one mixed-request proof;
no frozen C6 artifact, full261-case, full-suite, Linux or new native qualification
claim follows from it.


The post-Ruling26 current proof supersedes the preceding cut for current runtime claims. Actual Windows CPython3.11.9 compiled210/210 copied Python files at cut f6997ac529dfe43eefa5a17f97989d7ebe853caa2993af1266a0f6a1138c3034, with32 runtime/schema files,44 normalized implementation fingerprints and unchanged precertificate resources. Current copied3.14 API,3.11 API and unchanged3.11 CLI each emitted18 owners/123 schedules/125 bindings for the same11-instance mixed request, including Warehouse and Retail source parents and four physical services. All three scientific comparisons returned zero differences. Genuine positive source-parent composition succeeded through both the private verified-snapshot route and the public independently loading route; wrong snapshot type/RID, independently corrupted public resources, original-service-authority and both parent nested-reference mutations rejected.

The exact raw post-R26 report python311-c6-resource-reuse-compatibility-report.md has SHA256 afbf69fe146f58d14e725d4bfd5205d297eefd469d48621a604a071bc8c8672f; evidence is under build/task-10/python311-c6-resource-reuse-20261015-01. Its native-XZ proof is explicitly inherited only through exact decoder/dependency/lock/container identity from the earlier actual3.11 run, not newly decoded. Temporary own X: mapping and cleanup are disclosed; the initial pre-append report remains separately preserved. This is current-source Windows grammar and one mixed API/CLI/guard proof, not the frozen artifact, full261 request, complete suite, Linux or new native-method qualification.


Ruling27 changes only the development helper's named combined-reproduction allowance to600 seconds; generation remains240 seconds. Current cut03 SHA05bea30b61673e48fb1d44447a7898f0c51fed817e01b84664f6309598101265 contains211 Python files,32 byte-identical runtime/schema files and44 implementation fingerprints. Actual pinned Windows CPython3.11.9 compiled211/211 and passed the four focused helper tests. `build/task-10/python311-c6-helper-20261015-02.json` SHAa51d5b48ed2a908c51cfef077c6578ab05c123cd5fa888aeea8a879998d39c3c records this bounded proof. The earlier actual mixed/API/CLI and native-codec proof is inherited only after rechecking all32 runtime/schema files plus exact prior decoder/dependency/lock/container bytes; no new mixed/full261/frozen/Linux claim follows. The first helper probe compiled the same grammar and tests; the second added explicit codec dependency/container identity checks, with separate logs.
