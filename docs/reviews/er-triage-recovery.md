# Hospital ER_Triage magnitude recovery

Inspection date: 2026-10-11. Implements the source-recovery priority in ADR 0016.

**Recover 21.5278 W/m²** for the electric equipment of Hospital / DOE Ref
1980-2004 / ER_Triage (`program-a4ffe6755aa603f0cfcd`) from the original DOE/NREL
post-1980 Hospital scorecard. This is a magnitude-only source supplementation;
the frozen standards row remains null. No additional experimental magnitude
assumption is needed for this case.

## Source trace

The standards file at revision
`c8c1b9ebb30c5f1a441231bf3eae76b18fbbe907`,
`lib/openstudio-standards/standards/ashrae_90_1/doe_ref_1980_2004/data/doe_ref_1980_2004.spc_typ.json`,
has null at `/space_types/47/electric_equipment_per_area`. Its units are W/ft².
The row supplies the `Hospital Critical Equip` schedule and equipment heat
fractions latent 0, radiant 0.5, lost 0. It has positive occupancy of 20
people/1000 ft². No alternate absolute-power or per-person equipment operand
exists in this row. The atlas faithfully retained the null.

`Standards.SpaceType.rb:220–267` reads `electric_equipment_per_area`, applies
Ruby's `to_f`, and creates/modifies electric equipment only when the converted
value is nonzero. It therefore supplies no missing triage magnitude. This
conditional is not proof that an occupied clinical program should receive zero
equipment: it also leaves pre-existing equipment alone when the gate is false.
`Prototype.Hospital.rb:138–182` adds custom electric equipment to the kitchen
only and only for enumerated code templates. It provides no triage recovery.
The inspected Hospital geometry `ASHRAEHospital.osm` contains no
`OS:ElectricEquipment` object.

The [original DOE/NREL Hospital dataset](https://data.openei.org/submissions/157)
provides a separate **post-1980 v1.3_5.0 SI scorecard**. Its
[workbook](https://data.openei.org/files/157/refbldghospitalpost1980v1.35.0si.xlsx)
contains these literal cells:

| Locator | Original value | Interpretation |
| --- | --- | --- |
| `BuildingSummary!C4` | Hospital post-1980 construction | Correct existing-stock benchmark |
| `ZoneSummary!A8` | ER_Triage_Mult4_Flr_1 | Correct clinical program |
| `ZoneSummary!L2` | Elec Plug and Process (W/m2) | Electrical plug/process density in SI |
| `ZoneSummary!L8` | 21.5278 | Recovered W/m² magnitude |

These are stored values, not cached formula results. The transformation is
identity. The zone multiplier of four and zone area are not applied to an
already area-normalized density. The workbook is 733,597 bytes with SHA-256
`ab70c78f8dd33460089470b17c858ac6b5235241def2dda1fdb0658c80611459`.
It is attributed to Deru, Michael, et al., National Renewable Energy Laboratory,
2014, OEDI submission 157, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
as identified by the publisher's dataset page and official Data.gov catalogue.
The original workbook is retained unchanged in the ignored build cache;
retrieval is locked in the reproduction script and generated evidence.

This recovery uses the matching existing-stock benchmark, with its scorecard
version recorded separately from the standards revision. It is not a claim that
the pinned standards JSON reports this number, nor a claim that its complete
generated model reproduces the older scorecard. Keep the pinned standards
schedule `schedule-e4f94129c3eef678d03b` and heat fractions: this operation
recovers only the absent magnitude under the accepted source-first policy.

## Distinct comparison variants

The pinned pre-1980 triage row (`/space_types/46`) reports **2.67 W/ft²**,
equivalent to approximately 28.7396408 W/m² using the atlas conversion. The
selected 90.1-2007, 2013 and 2019 code rows report **2 W/ft²**, approximately
21.5278208 W/m². Neither is substituted for the post-1980 value. In particular,
the recovered literal **21.5278** retains its published precision instead of
silently taking the nearby code value or borrowing the pre-1980 value.

## Reproduction and integration

The supplementary record is [er-triage-v1.json](../../data/program-inputs/er-triage-v1.json).
It provides the source program ID, `status: recovered`, `value_W_m2`, source
locators, original units/value, transformation, extraction date, source hashes,
attribution and an interpretation note. Original-source nulls remain evidence.
Use this record when resolving the matching leaf before mixture aggregation.
Do not apply it to other vintages or positive reported loads.

```powershell
.venv/Scripts/python.exe -m scripts.investigate_er_triage --fetch
.venv/Scripts/python.exe -m scripts.investigate_er_triage --check
.venv/Scripts/python.exe -m unittest tests.test_er_triage
```

`--fetch` retrieves the workbook only if absent and verifies its locked hash
before writing. It never replaces an existing source file. Normal generation
and `--check` use local bytes only. The standards archive must already exist at
the location governed by `sources/commercial-runtime-lock.json`; its SHA-256 is
verified before inspection. The script reads the standards members directly
from that archive and records each member hash. No upstream model code or
EnergyPlus simulation is executed.

Validation verifies the workbook hash/size, exact stock/zone/unit labels,
positive literal magnitude, matching unresolved frozen leaf, source-archive
checksum, and deterministic output. Tests reject another stock variant,
changed units/program, missing or nonpositive magnitude, and checksum changes.
Exporter integration and the broader release-validation gates are separate
from this source investigation.
