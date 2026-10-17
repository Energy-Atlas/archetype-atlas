# ADR 0034: Case-matrix release layout 3 with a streaming reproducer

> Superseded by ADR 0035 (2026-10-17): verification and release ceremony removed.

Status: accepted (rulings 145–147); first used by v0.8.0.

The cumulative apartment request (313 programmes, 385 requested owners) cannot
be generated in one ordinary call within 240 seconds on current Python, and its
1,092,759,826-byte reference cannot be parsed into one Python graph within the
memory available to the full-reference check. ADR 0033's layout 2 reproducer
parses and compares whole graphs, so it inherits both problems.

Release manifest schema `3.0.0` keeps layout 2's four local files
(`manifest.json`, `generator.zip`, `reproduce.py`,
`references/all-cases-bundle.json.gz`) and its transport rules: every file and
member at most 104,857,600 bytes, exact member and reference identities, and
producer provenance. It adds a `case_matrix` descriptor with contract version
`1.0.0`: the fixed case order, one exact request member per case
(`references/case-matrix/<case>.request.json`), the three admitted matrix
inputs (`case_matrix/inputs/`) and the packaged adapter and comparer modules
(`case_matrix/`). The original one-call request stays as
`references/all-cases-request.json` for provenance; its single-call 240-second
bound is not claimed. The reference is the retained official-3.11 one-call
output, and its `producer_python_version` is recorded.

`reproduce.py` is copied byte for byte from
`scripts/schedule_generator_case_matrix_reproduction.py`. It verifies the
release, extracts the ZIP, admits the packaged matrix, checks that the packaged
case and full requests equal the admitted ones, and generates both cases with
the packaged `generate()`, which validates each case. It then emits the
original union piece by piece in canonical byte order and compares it in
lockstep with the stream-decompressed reference; neither side is held as one
graph. The union is not revalidated: equal canonical bytes mean an equal value,
and the reference was validated when it was generated. When the interpreter
differs from the producer, only `rng.python_version` inside commercial RNG
receipts is rewritten, and only if the packaged comparison policy lists it in
`ignored_administrative_fields`; every substitution is counted. Any other
difference fails with its byte offset and JSON pointer.

Gates are unchanged in value: each case through the ordinary
`python -I -S generator.zip --request … --output …` boundary within 240
seconds, and one complete reproduction within 600 seconds, on current Python
and official Windows 3.11, each measured separately. Layout 3 ZIP-only
`--reproduce` exits 2. Layout 2 rejects schema 3 and layout 3 rejects schema 2;
historical releases keep their routes. Public request and bundle schemas, the
generator API and CLI, resources, source proofs and comparison tolerances are
unchanged.
