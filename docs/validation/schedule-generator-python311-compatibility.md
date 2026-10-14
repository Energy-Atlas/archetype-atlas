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
