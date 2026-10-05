# Selective schedule resolution review

One fresh whole-branch review covered `aff4d3f..2708f97`, including the
evidence gates, executed profiles, immutable supplement, provenance, catalogue,
workflows and documented scientific boundaries. It found no Critical or Minor
issues and no declined-to-judge items.

The Important finding was failed-generation lifecycle handling: an unsuccessful
rerun could leave a prior index in the reused directory, allowing stale profiles
to be frozen. Generation now creates a fresh attempt and durably records running,
failed or completed status before retrieval/execution. Freezing accepts only the
latest completed receipt with matching record inventory and index checksum.
Earlier successful files remain intact but cannot conceal the latest failure.

Regression tests demonstrated failure before the first output and after partial
unchanged output, and blocked freezing a previous successful raw directory.
They failed on the reviewed implementation and passed after the correction.
All 67 Python and eight Node tests then passed. A fresh actual upstream run of
all 41 configurations reproduced the frozen profile index and every CSV/JSON
artifact byte for byte; the completed-receipt freeze path also validates.

The reviewer independently checked all 677 resolutions and all 41 profile
hashes, CSV/JSON equivalence, contextual inputs and absent-use gates. Remaining
weather proxy, nominal thermostat/unavailable-day and zero-occupant boundaries
are explicit limitations, not implicit simulation readiness.
