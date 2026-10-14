Each `*-request.json` contains `{schema_version, params, seed}`. Call
`atlas_schedules.generate(request['params'], request['seed'])` to obtain the
complete corresponding `*-bundle.json.gz`. Bundles contain all 8,760-sample arrays
and source/seed/budget receipts as compact JSON, compressed without a current
timestamp or filename. Decompress with Python's standard library:

```powershell
python -c "import gzip; from pathlib import Path; p=Path('docs/examples/schedule-generator-v1/medium-office-bundle.json.gz'); p.with_suffix('').write_bytes(gzip.decompress(p.read_bytes()))"
```

Compare realizations with `atlas_schedules.comparison.compare_bundles`
and the current packaged comparison policy, rather than generated file hashes.

The Medium Office pilot samples its operating group once. The two-apartment
pilot includes source-occupied and source-vacant units in one ordered native
allocation. The mixed-family pilot binds explicit physical extents and an
experimental result area; the request does not infer apartment floor area.
The all-declared-cases pilot retains all ten separate source/reviewed M1 cases,
including both accepted-inactive Plenum owners with no fabricated schedules.

Reproduce the examples with:

```powershell
python -m scripts.schedule_generator_examples
```

Public M1 is the exact packaged case/configuration/weather/template set in
calendar 2007, local standard time, with no implicit holidays or DST. These
pilots describe energy semantics and seeded source adaptations; they do not
claim national population realizations. See ADR 0023 for physical mixture,
representative control, shared identity and precomputed-bundle contracts.
