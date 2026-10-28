# Answer keys

An answer key is a small, frozen file of correct outputs recorded once from the
real upstream software: OpenStudio 3.10 / Ruby 3.2.2 running ComStock,
openstudio-standards 0.8.6 or OpenStudio-HPXML code, or the frozen v0.8.0
legacy generator. Each key keeps the inputs that matter (rule sets, seeds,
sampled parameters) and the expected hourly results, packed compactly: an
8,760-hour array is stored as its distinct days plus a 365-entry day index,
and random residential channels as daily sums plus sampled hours.

The tests in `tests/schedules/` rebuild every case with the Python generator
and require agreement within ADR 0035's tolerance: fractions within 1e-6,
annual totals within 0.01 % and discrete outcomes exactly. Keys let the port
prove it matches upstream without OpenStudio or Ruby installed, and they catch
regressions immediately.

To add or refresh a key, capture it with a harness in `scripts/capture/` and
extract it. The current rerunnable captures are `scripts/capture/commercial_families.py`
and `residential_dominant.py`, extracted by `scripts/answer_keys/family_programmes.py` and
`residential_dominance.py`. The occupancy-dominance capture built its inputs from the
frozen definitions and left with them in stage X1.3 (ADR 0046 section 7); it is readable
at the tag `frozen-data-2026-10-27`, and its key stays.
The other extractors ran once during the 2026-10-17 restructure. Their inputs
(`data/schedule-generator/`, `data/generator-releases/`) were deleted and
purged from history, so the extractors were retired. They remain readable in
commit `779f9fb` under `scripts/answer_keys/`, with the migration scripts under
`scripts/migrate/`.

| Key | Checks | Source | Test | Extractor |
|---|---|---|---|---|
| `commercial/kernel-cases.json.gz` | ComStock transform, 11 controlled cases, every slot | native capture `commercial-vectors.json` (`scripts/capture/commercial.rb`) | `test_commercial_kernel` | `commercial_kernel.py` (779f9fb) |
| `commercial/families.json.gz` | 926 programme cases and 40 restaurant water cases of Medium/Small Office, Warehouse, Retail and both restaurants | native family captures, OpenStudio 3.10 | `test_commercial_families`, `test_recipes_native` | `commercial_families.py` (779f9fb) |
| `commercial/family-programmes.json.gz` | 534 cases, 2,834 slots of the nine newer families (one template each, both views, seeds 42/51) | `build/task-10/native-family-programmes-20261017` | `test_family_programmes_native` | `family_programmes.py` (live) |
| `commercial/family-pilots.json.gz` | People per space on real prototype geometry and water, 8 pilots (Large Office, Large Hotel, Hospital, Outpatient, 90.1-2013) | native pilots `build/task-10/native-*-pilot-20261014-01` | none since stage X1.3 (its test read the frozen definitions) | `family_pilots.py` (779f9fb) |
| `commercial/occupancy-dominance.json` | residential/non-residential design people per configuration (150) on real prototype geometry | `scripts/capture/occupancy_dominance.py` | `test_residential_dominance_native` | `residential_dominance.py` (live) |
| `commercial/residential-dominant.json.gz` | 20 inverted rule-day cases: real guest/patient-room carriers and crafted default-profile stress cases | `scripts/capture/residential_dominant.py` | `test_residential_dominance_native` | `residential_dominance.py` (live) |
| `commercial/stripmall.json.gz` | Strip Mall 2013 source pilot, seeds 42/51 | native Strip Mall pilot extract | `test_stripmall` | `stripmall.py` (779f9fb) |
| `commercial/sampling-draws.json` | 6,660 operating-parameter draws | ComStock `sampling/tsv_sampling.py` (3c103063) on supplied uniforms | `test_sampler` | `sampling.py` (779f9fb) |
| `residential/cases.json`, `channels.npz` | 57 ResStock units: channels, occupant types, offsets | Ruby 3.2.2 running OpenStudio-HPXML `BuildResidentialScheduleFile` (dd25369) | `test_residential_r1` | `residential.py` (779f9fb) |
| `residential/ruby-draws.json` | 8,250 Ruby `Random` draws (R1 stream) | Ruby 3.2.2 | `test_residential_r1` | `ruby_draws.py` (779f9fb) |
| `orchestration/programmes.json.gz` | 189 single-programme outputs (121 compared; rebuilt Office/Warehouse skipped) | frozen v0.8.0 generator, a regression baseline, not native | `test_programmes_legacy` | `legacy_programmes.py` (779f9fb) |
| `orchestration/case-matrix.json.gz` | two A5 case-matrix requests (365 of 463 owners compared) | frozen v0.8.0 generator | `test_case_matrix_legacy` | `legacy_case_matrix.py` (779f9fb) |
| `orchestration/mixtures.json.gz` | six mixture scenarios (four compared) | frozen v0.8.0 generator | `test_mixtures_legacy` | `legacy_mixtures.py` (779f9fb) |

`retired-doe-ref.json` lists the DOE Ref recipes, configurations and services
that stage X1.2 replaced with recipes written from atlas release 2.0.0
([ADR 0046](../../docs/adr/0046-release-2-0-0.md) section 6). The keys keep
their captures of those inputs; the tests skip the cases that name them.

The ResStock dwelling, apartment-unit and fixed recipes were converted from the
legacy package by `scripts/migrate/recipes.py` (779f9fb) and are now plain
data; the residential and orchestration keys above protect them.
