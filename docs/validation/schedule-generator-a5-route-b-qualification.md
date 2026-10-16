# A5 case-matrix full-reference qualification (Route B)

On 2026-10-16 the two-case apartment A5 matrix reproduced the retained
one-call reference exactly on official Windows CPython 3.11.9 and on CPython
3.14.7. This closes the full-science comparison that R128 (`frame_limit`) and
R140 (diagnostic only) left open. The layout-3 release v0.8.0 then passed the
packaged per-case and full-reproduction gates on both runtimes (below).

## Method (ruling 145)

`scripts/schedule_generator_case_matrix_qualify.py` generates both cases with
the public `generate()` API from the admitted production inputs
(`tests/fixtures/schedule_generator_case_matrix/`), redirecting only
`ResourceSet.load` to the extracted production resource set
`resources-7aee18c5b76b6ca18baf01e820115c07ee78be9d97ee20c5b58b2208fafc0507`.
`stream_original_union`'s checks then run on the cases, and the union is
emitted piece by piece in canonical byte order and compared in lockstep with
the stream-decompressed reference. Neither side builds or parses the whole
1.09 GB graph. `generate()` validates each case; the union inherits strict
validation from the reference by exact byte equality (R145).

The reference is the retained official-3.11 one-call output,
`build/task-10/apartment-a5/profile/post-r70-python311-actual/candidate-v0.8.0/references/all-cases-bundle.json.gz`:
65,467,798 bytes, SHA-256
`62ccd3e3b6a11b2ad81d34b51c8157164f2d96365bd3efc24398e76eda0e583b`;
decoded 1,092,759,826 bytes, SHA-256
`06bfc6aa7d01d0cc76fd099616a7ac94ab2ba807220ff4653cea5ba5dfb6e33d`.
The candidate's `generator.zip` (SHA-256 `5799bb2c…`) supplied the resource
set; its 35 `atlas_schedules` modules are byte-identical to the source tree.

## Results

| Run | Runtime | Code | Result | Total | Case 1 / case 2 generation | Peak commit |
| --- | --- | --- | --- | ---: | --- | ---: |
| run-311-001 | 3.11.9 | d910f11 | MATCH, exact, no normalization | 291.5 s | 116.6 s / 71.2 s | 4.14 GiB |
| run-314-004 | 3.14.7 | b148017 | MATCH; 376 `rng.python_version` values normalized | 274.9 s | 108.2 s / 66.5 s | 4.11 GiB |

Both runs streamed 6,007 pieces and matched every byte. The 3.14 run rewrote
only the interpreter version inside commercial `rng` receipts, a field that
`atlas_schedules/data/reference/comparison-policy.json` already lists under
`ignored_administrative_fields`; every schedule value and float was identical.

## Adverse attempts, retained

| Run | Outcome | Cause | Change made |
| --- | --- | --- | --- |
| run-314-001 | Watchdog stop (exit 3) | Machine commit fell to 1.04 GiB during case re-validation | Runner relies on `generate()` validation; faster `_identity` |
| run-314-002 | Watchdog stop (exit 3) | Eager union copies added about 2.2 GiB to 4.1 GiB of cases | Owners and bindings remapped lazily (d910f11) |
| run-314-003 | MISMATCH at `/constituents/1` | `rng.python_version` 3.14.7 versus 3.11.9 | Policy-backed normalizer (b148017) |

## Receipts (ignored local evidence)

Directory `build/task-10/apartment-a5/route-b/`:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| run-311-001.json | 10,479 | `69c23c75926887006109aab611bf26ae34bab3fe4f0762baf1869a03a0324280` |
| run-314-004.json | 10,673 | `6dea4f69614103084a7c6cc8c25a232b33fb6c7e4b0d603e92ebb70051be69ca` |
| run-314-003.json | 10,940 | `d842f64bb13eebb2ba1a5ea8e420f0829abfe9fcc9dfff57f19a4adb454a4fcd` |
| run-314-002.json | 8,693 | `0b8e0d2b7a3a7f2f456424125b43a2d631fbd7d5d0e25ebc67f6461dd6a96cdb` |
| run-314-002.memory-stop.json | 534 | `2069739dc3818e0e2012c734a160a67f0f8c4a8d6b8e08cf96797e667eb19cce` |
| run-314-001.json | 2,961 | `918d2c8ce2598febafce91fc839a8e452d3eb1bc14b580f16299204639c3b34d` |
| run-314-001.memory-stop.json | 381 | `e3cba66ee313e33a94adf6e295c3c0a1fa9f5107c980e607f92f1fe3a4d3e50a` |

Receipts record argv, interpreter, UTC times, per-phase seconds and process
memory, watchdog minima, every `atlas_schedules` module hash and git state.

## Layout-3 release gates (v0.8.0)

The release `data/generator-releases/v0.8.0` is byte-identical to the gated
candidate `build/task-10/apartment-a5/layout3/candidate-v0.8.0-r2`: manifest
`85c2370a…`, `generator.zip` 102,322,125 bytes `bb1eb96b…`, `reproduce.py`
`996a64f2…`, reference `62ccd3e3…`. Each gate ran in its own child process,
guarded by a 1 GiB commit floor, with nothing else heavy on the machine.

| Receipt | Runtime | Case 1 | Case 2 | Reproduction |
| --- | --- | --- | --- | --- |
| profile-314-002.json (16,294 B, `e7af44c6…`) | 3.14.7 | 141.5 s | 98.7 s | 330.3 s MATCH, 376 version rewrites |
| profile-311-003.json (16,583 B, `0b2eb344…`) | 3.11.9 | 154.3 s | 100.2 s | 377.9 s MATCH, exact |

Superseded or invalid profile runs are retained: the first candidate's
profile-314-001 passed but preceded review fixes; profile-311-001 and
profile-311-002 were stopped by the memory floor because other processes
(an orphaned review `grep`, another session's tests, then editor start-up)
held the machine's commit. Child peaks in those runs stayed at or below
3.64 GiB.

## Limits

- Windows only; no Linux evidence.
- Measured on a shared 32 GB machine; the full reproduction needs about
  4.3 GiB of free commit plus headroom.
