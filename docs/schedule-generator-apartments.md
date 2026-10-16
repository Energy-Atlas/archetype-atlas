# Offline schedule generator: cumulative apartment milestone (v0.8.0)

v0.8.0 adds the apartment family (milestones A1–A5) to the cumulative
residential and commercial generator. The cumulative scope is 313 exact
programme methods, 84 of them apartment programmes, and 30 source
compositions: 385 requested owners, which expand to 463 owners, 2,754 hourly
schedules and 2,778 bindings. Packaged resource identity:
`resources-7aee18c5b76b6ca18baf01e820115c07ee78be9d97ee20c5b58b2208fafc0507`.
This is 313 of 1,900 programme methods and 30 of 378 compositions; unknown gas
and additional loads and other recorded source exclusions stay unresolved, so
the full extraction remains open.

The release manifest is authoritative for the shipped artifact. Source-method
coverage is in `docs/validation/schedule-generator-apartment-coverage.json`.
That report is built from the development resource root
(`resources-1de2abc9…`); freezing rewrites the runtime scope and case list,
which gives the packaged set its different identity, as for earlier
milestones. Regenerate or check it with
`python -m scripts.schedule_generator_coverage --scope a1 [--check] --resources-root DIR`;
the default root, `build/task-10/apartment-a5/resources`, is local and untracked.

## Using the release

The release is `data/generator-releases/v0.8.0` in layout 3 (ADR 0034). The
cumulative request is split into two exact cases that keep every original
owner, native unit position, seed, operating group, alias and reference:

| Case | Requested owners | Output owners | Schedules | Bindings |
| --- | ---: | ---: | ---: | ---: |
| `unit-chain-and-caller-closure` | 165 | 165 | 1,384 | 1,408 |
| `commercial-group-and-source-parent-closure` | 220 | 298 | 1,370 | 1,370 |

The case requests are members inside `generator.zip`, at
`references/case-matrix/<case>.request.json`. Extract one and run, offline
(tested with Python 3.11.9 and 3.14.7 on Windows):

```powershell
python -I -S release/generator.zip --request work/<case>.request.json --output work/<case>.bundle.json
python -I -S release/reproduce.py --release-root release --receipt work/reproduction.json
```

`reproduce.py` regenerates both cases and requires their union to equal the
one-call reference (`references/all-cases-bundle.json.gz`, 1,092,759,826 bytes
decoded) byte for byte. It streams both sides and needs about 4.3 GiB of free
memory. The original one-call request is kept as
`references/all-cases-request.json` for provenance only; a single 385-owner
call is not claimed to finish within 240 seconds.

## Qualification on Windows (2026-10-16)

| Gate (limit) | Python 3.14.7 | Official Python 3.11.9 |
| --- | --- | --- |
| Case 1, packaged CLI (240 s) | 141.5 s, 2.80 GiB | 154.3 s, 2.82 GiB |
| Case 2, packaged CLI (240 s) | 98.7 s, 3.37 GiB | 100.2 s, 3.43 GiB |
| Full reproduction (600 s) | 330.3 s, 4.25 GiB, MATCH | 377.9 s, 4.29 GiB, MATCH |

Memory is peak commit of the child process. On 3.14 the comparison rewrote
376 `rng.python_version` values from 3.14.7 to the reference's 3.11.9, the only
difference allowed (comparison policy `ignored_administrative_fields`); 3.11
matched with no rewrite. Case 1's ordinary output is byte-identical on both
runtimes; the ordinary case outputs are timed and hashed, while the union
comparison regenerates the cases in process. Receipts and the earlier
attempts, including four memory-floor stops on a shared machine, are listed in
`docs/validation/schedule-generator-a5-route-b-qualification.md`.

## Limits

- Windows only; no Linux run was made.
- `generator.zip` is 102,322,125 bytes, 2.5 MB under the 104,857,600-byte
  per-file cap, so layout 3 has little room to grow.
- The union is not revalidated; it is byte-equal to the reference, which
  `generate()` validated when it was produced (ruling 145).
