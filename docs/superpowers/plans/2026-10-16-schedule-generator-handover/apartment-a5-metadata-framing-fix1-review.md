# R142 metadata-framing fix1 — independent BOTH source and finite review

**Specification: PASS within R142 source and finite scope. Code/task/evidence quality: PASS within that scope. New findings: C0 / I0 / M0.** No new breakage requiring a change was found. This qualifies the prospective parser candidate and its supplied finite evidence only. The main full-science frame_limit and future explicit final-cache validation requirements remain OPEN.

Same independent reviewer, no children. Isolated root: `<WORKTREE>`. M is `build/task-10/apartment-a5/framed-reference-v1/metadata-framing-fix1`; H is its sibling `oracle-framed-fix1`; C is sibling `candidate-io-fix1`; SDD is `.superpowers/sdd/2026-10-13-schedule-generator`. No R143 transition-plan review or next execution authority is supplied.

## Authority and authenticated cut

Read the exact R142 review brief first, 3945 B / `c7e2923f4cc7ccc84eb91a7a7cdec313ada23728537a54b5482f265f765992b9`; implementation brief 10069 B / `0622cdb61f39c208ada4f09a9e23dffbf98cf0815625b7b5052fa02cebed8b07`; accepted design 8154 B / `b825c55bb84771c59c6cde08afa906cd0708c3248e91221433ab8e2ef4359f04`; and empty-fixture addendum 1176 B / `c770deaf395386ca4fc50414ef8af45ed6959a8e9fda285b31d49dced6662169`. The addendum explicitly permits the manifest-declared zero-byte synthetic case without changing its identity or expected outcome.

Owner report 7930 B / `9bfa025dc59264ccab93fefe5afaa85f298208b28cdc9062c644755a7a8303ae` matches the index/seal/report links. Authenticated every one of the 185 indexed raw files, including all 139 synthetic fixtures, raw stdout/stderr/receipts, baseline/candidate/kernel, manifests, source utilities, freezes, inverse proof and retained adverses. Exact new M membership is 189 files: 185 indexed plus these four explicit exclusions: closure-index.json, closure-receipt.json, closure-seal.json and closure-sidecar.json. No hidden extra file or undeclared exclusion was found.

| Closure file | Bytes | SHA-256 |
|---|---:|---|
| closure-index.json | 31648 | 804c838d411e09ecd6ab93c30785f3eae3bdd8fbc9ae8d7c397a9627b0b0753b |
| closure-seal.json | 955 | f9eca3d380279b6981010b8ca8b992cd84011743dd490a1aac6ffc69a8e23811 |
| closure-sidecar.json | 551 | ce7fda3c93d9e92e5d8ba49f99096d04cf4a7b0a65bb5ff97cb2ba3ec0852791 |
| closure-receipt.json | 1174 | df70ba3a8d3594932ba58ad41ed6286d666da6f18c2034ebcd30bf90635a1d90 |

The receipt is an explicit unindexed cycle exclusion, not an implicitly sealed index row. Its current raw bytes and reciprocal report/source/index/seal/sidecar identities were inspected; this review records its raw pin. The index honestly says final fixture entries reuse pre-RED identities and earlier verification. I independently hashed all current indexed fixture bytes, rather than treating that reuse as a new owner payload read.

## Source assessment

Candidate M/framed_reference.py is 15183 B / `232cc1e27536b871f6503b8156011bf7a5bdad61dca7a283fb68234806a162f3`. Named H source and M baseline are byte-identical at 13679 B / `09f47872b8c5a6603b9fb7b705383305af9d8f7e3690782e918425f4ac02702b`. Both kernels and baseline kernel are byte-identical at 1043 B / `2f49ca19ad483d08bce5887bf2e15b04f57eff0bd859dea23b0dd6f69c992b10`.

Independently replayed all four byte edits forward and backward using their documented sequential-source offsets, reconstructing exact candidate and baseline. Regenerated full unified diff matches cut1-full.diff byte-for-byte. Independent AST comparison finds only array/root changed among existing reader methods and metadata added. The entry API, other methods, kernel and constants are preserved.

`array(parent_depth=1)` keeps the original root-array depth and gives metadata's array parent_depth=2: metadata depth2, array3, realization-object4. Exact decoded root metadata plus object dispatch opens only that object. Its strict key reader rejects duplicate decoded keys, including escaped aliases, before insertion. Only decoded building_realizations with an array value opens the second container; other metadata fields and nonarray realizations remain strict bounded frames. Nonobject metadata retains its previous root-array or ordinary-frame branch. No generic recursive split, hardcoded eight-record assumption, measured offsets, program/seed allowlist, field omission, coercion or schema change appears.

Order and ordinary dict/list construction are retained. Metadata consumes whitespace after an opened array before checking its separator, rejects missing separators/adjacent values and trailing commas, and clears partial results and retained buffers on failure. Prefix overflow is discarded only when opening the selected container; ordinary atoms still reject it. Streams remain read-only/nonseekable and caller-owned; one live frame text/decode, per-call kernel pooling, strict numeric/duplicate handling, ASCII digest and separate positive read(1) EOF are unchanged.

All original caps remain: frame8388608, key65536, root64, metadata/map131072, global value frames131072, depth256 and read65536. Oversized realization primitives, realization objects and other metadata atoms still reject frame_limit. Intentional accounting opens metadata and its selected array instead of counting those envelopes as atoms; individual retained children count. Original observational expectations did not require an exception or modification.

## Genuine RED and fixed finite evidence

red-freeze.json is 29732 B / `dec5d6acf3f0304361a24139b4cf1eb42eeed90f8e7309890b051d9100d50609`; cut1-freeze.json is 29853 B / `160cf081ac69caa84074c7b3a41d7da1cc9b6b542a965b3154cc76a38955e134`. Their source rows match authenticated current bytes and their identical 139 fixture identities match the current raw fixtures. Test/kernel/manifests stay fixed across RED/cut1. The implementation utility requires the recorded genuine RED and candidate absence before exclusive candidate creation.

RED runs the pinned baseline module, not the candidate or legacy read-failure adapter. metadata_big is 9437323 B / `95841850671e0be3a8a57c46c5fc8ab099043d08dc695d4621758548871edffb`: synthetic three-record construction with three 3MiB strings makes metadata and its array exceed8MiB while each record remains bounded. Raw RED records actual ValueError(frame_limit), framing_enter/resource rejection, 129 bounded reads/8454144 delivered bytes, candidate absent and one caller close. This is a parser failure, not a harness failure.

| Window | Runtime | Raw capture seconds | Outcome |
|---|---|---:|---|
| RED | 3.14.7 | 0.9631810001 | EXPECTED_RED |
| NEW314 | 3.14.7 | 8.5742362000 | 47/47 GREEN |
| REG314 | 3.14.7 | 5.6931136000 | 1229/1229 GREEN |
| NEW311 | 3.11.9 | 8.5266513000 | 47/47 GREEN |
| REG311 | 3.11.9 | 5.5120513000 | 1229/1229 GREEN |

All five raw receipt pipe identities match actual raw stdout/stderr; every exit is0, timeout false, stderr empty, readers finished and reader_failures empty. Commands use the declared absolute executables, -I -S -B -X utf8, owned M cwd and frozen finite_entry.py. Recorded origins route RED to M/baseline and every GREEN to M/framed_reference.py and M's unchanged kernel/harness/stream. The entry verifies freeze source bytes before imports and calls the actual imported loader through a transparent observation wrapper. No mock or cached old candidate route was found.

Raw chronological windows are distinct and sequential. All four GREENs use cut1 and the same freeze identity; no cut2/window replay is present in the closed package. Capture sum is29.2692334001s; available tool-wall figures total about29.743s. Each is far below its60/30s cap and declared300s aggregate. Capture elapsed starts before child creation but precedes receipt/console writes; available tool-wall figures are explicitly transcribed, not raw OS creation facts. This ordinary finite runner does not qualify native Job/cold-runtime/control-plane policy.

M's original corpus_harness.py, stream_double.py and corpus-manifest.json match exact named C source bytes. Original manifest is276833 B / `43fd563c946a2f7e4cd2cb949d4c4fa7372180b8fd03f3f1c96c731892e2032b`. All92 fixture paths/identities, all1229 evaluations, original typed descriptors, outcomes, order/bit checks, three sensitivity controls and observational expectations remain unchanged. Relative corpus paths are remapped only by the owned directory parent. Each runtime records125847614 semantic bytes,1230 candidate invocations/releases including independence, and1229 baselines.

New manifest120861 B / `5b9fd8214bd3bdb79e2e40a6cebea493e389d7fc6559565ab837e7288b18967a` contains47 evaluations and99240162 semantic supplied/baseline bytes per runtime, below its separate128MiB window. Independently recomputed every new evaluation's payload charge, including extra EOF byte and repeated baseline reads. Eight resource-only cases explicitly omit baseline graphs; 39 baselines and47 candidate invocations/releases are recorded. No primitive bytes are omitted from those resource charges.

Source/manifest coverage includes empty/one/three/nine realizations, metadata and realization type fallbacks, exact graph/types/order/binary64 bits, escaped aliases/duplicates at all three levels, strict separators/trailing commas/escapes/numeric failures, int4300/4301, all relevant resource boundaries, selected-envelope prefix overflow, oversized retained atoms, one-byte/short reads, EOF/length/hash and operational failures. Frozen harness checks caller close and release balance, two semantic roots maximum, strict-kernel differential graphs and independent descriptors. Both runtimes record new24 materializations/10 semantic/8 resource rejects; original409 materializations/784 semantic/21 domain/6 resource rejects. Observed maximum frame8388608/key65536/depth256/read65536/live texts1/live decodes1 agree on both. These are finite observations and source contracts, not independently measured RSS or full science.

## Adverses, historical finding and limits

Retained preparation guard failure for the known empty synthetic fixture is prospectively resolved by the exact addendum; the empty case was preserved, never interpreted as unknown/zero substitution. Retained close.py bytes-serialization TypeError and close-002.py report8235>8192 failure are metadata-only adverses. Numbered close-003 preserves candidate/tests/fixtures and records reused prior verification; neither adverse is disguised as a parser result or consumes a new cut. Available adverse tool exits/walls are transcriptions with explicit source callsites, not fabricated raw OS telemetry. Current closure counters conservatively report preparation129539488 B and closure89005106 B, each below its128MiB phase cap.

Authenticated cache erratum2170 B / `8f0adf64176fe1bc29bbd2b72a5d35ccd90e6d46ed6940507024cdef0e31773e` against the prior accepted review12491 B / `259aed3814e0a9528efd364796d317db4a099f200a86e77729cad928d4b5a535`. It explicitly withdraws R140 reportline21's unsupported final-cache inference, retains historical overall specFAIL/qualityFAIL C0/I1/M0 and postrun cache absence NOT_EMITTED. It does not infer cache presence or measurement corruption, probe later state, or claim recovery. Reporting correction is addressed; missing historical runtime evidence remains unavailable. Scoped lexical topology can support this source change without qualifying strict semantic/full-science behavior.

Disposition: prospective parser SOURCE+finite requirement is addressed by this cut. Main full-science frame_limit Important and explicit final-cache source+actual Important remain OPEN until separate coupled full qualification. R140 remains FAIL history; retired001/R136 resolver history and R139 STOP history remain unchanged. Seven validators, compile/routes/original union/full canonical-byte comparison are not supplied or qualified by this task.

Incremental reviewer content reads, including repeats and failed-analysis reads: **86482521 B across278 successful file opens**, maximum9437323 B,201 distinct files, below192MiB incremental and16MiB/file. Three additional failed named opens were guesses for closure filenames inside M and read zero bytes. One own inverse-check assertion used baseline-relative offsets instead of the producer's sequential-source convention; inspection corrected that assumption and both independent replays then passed. No artifact was changed. One combined source display truncated; focused complete preparation/source views and bounded static verification supplied the omitted evidence. Report write/readback is excluded from input counters.

Own original-inventory target resolution/query/open, original reference/archive/runtime-binary/EPW/R122 access, prepared/test/helper/controller/project execution, parser replay, native/admission probe, Git/network, source fix, actual run and subagents: zero. Explicit named H/C source metadata and new M synthetic files were allowed SOURCE inputs; no inventory traversal occurred. Only new M membership was enumerated. Exact reviewer runtime model identity is unavailable. Sole write is this review. STOP.
