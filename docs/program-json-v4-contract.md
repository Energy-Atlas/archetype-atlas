# Program JSON 4: draw-only water-heating energy

**4.0.0 is an opt-in ready export.** The published catalogue still supplies
Program v3. Its frozen definitions, raw data and generated library are unchanged.
[ADR 0018](adr/0018-draw-only-program-water-heating-energy.md) defines the scope;
[the schema](../schemas/program-json-v4.schema.json) enforces the new contract.

## Migration and use

Version 4 starts with the v3 defaulted program and moves every active `hot_water`
load into `water_heating[].draw`. Non-water loads, schedules, approved program
defaults and source metadata keep their existing meanings. The draw retains its
demand ID, SI volumetric magnitude, scaling basis, schedule, target-temperature
schedule and EnergyPlus 25.1 `CorrelationFromWeatherFile` mains policy.

Each recipe embeds one heater conversion stage, or main then booster stages,
with source fuel, dimensionless conversion efficiency, source outlet temperature
and provenance. Nominal prototype capacity/volume select the source efficiency
rule; they do not size the consumer's heater or limit this simplified demand.
The source runtime's efficiency setter is executed. EF/UEF are not substituted
for conversion efficiency. Large gas-heater source calculations use loss terms
to recover the burner efficiency; this does not include standby energy in the
exported load.

The simulation evaluates embedded flow/target schedules, derives mains
temperature from its weather, and applies the draw's area, dwelling, person or
absolute basis once. It supplies `water_density_kg_m3` and
`water_specific_heat_J_kg_K` explicitly. These are fluid-property inputs, with no
new Atlas constant defaults. For comparisons with EnergyPlus, use the engine's
water-property convention consistently across reference and simplified models.

For one stage, instantaneous fuel input is
`rho * cp * scaled_flow * max(target - mains, 0) / efficiency`, in W.
For a booster draw, the main stage heats from mains to the lesser of the draw
target and main outlet; the booster supplies the remaining lift. Each stage
uses its own fuel and conversion efficiency. A fixture mixed below the tank
setpoint uses the delivered-water lift, not the tank setpoint lift for its entire
mixed draw. Annual energy requires integration over the simulation calendar and
weather; the JSON does not claim a fixed annual kWh value.

`draw_heating_power` and `evaluate_recipe` in
[the exporter](../scripts/program_water_heating.py) provide focused reference
calculations. `evaluate_recipe` consumes evaluated schedule values and the
required geometry/fluid bindings; it does not replace an EPW or schedule engine.

`ownership: instantiate_once` and `service_id` preserve a shared demand's
identity. Other recipes are applied per program instance. A consumer must dedupe
shared IDs across assigned programs. Shared host binding remains necessary for
service assignment, not for a tank-loss ambient model. Water-heating fuel input
has `zone_heat_gains: excluded` and is not an indoor equipment gain.

Choose these fuel recipes **or** explicit equipment heating for each demand.
Do not send the nested draw to a detailed heater while also consuming its
simplified fuel energy. V4 validation rejects active duplicate volumetric loads.
The unchanged v3 export remains the alternative for detailed equipment modeling.

Standby losses, heater pump/control electricity and pilot consumption are
explicitly excluded. Detailed source evidence remains in system inputs. The
solar-equipped residential program `program-1a9bafb870d938bc1ff6a0ee` fails v4
export as out of scope; its v3 program, draw and detailed solar evidence remain.
Heat-pump water heaters are not present in this recovered inventory. Adding them
requires a new performance contract; no burner-efficiency substitute is supplied.

## Recovery, coverage and focused validation

Run from the repository root:

```powershell
.venv/Scripts/python.exe -m scripts.fetch --lock sources/dhw-conversion-evidence-lock.json
.venv/Scripts/python.exe -m scripts.recover_dhw_conversion --check
.venv/Scripts/python.exe -m unittest tests.test_program_water_heating
.venv/Scripts/python.exe -m scripts.validate_program_water_heating --check
.venv/Scripts/python.exe -m scripts.program_water_heating --program program-8c35a40eb0181596e0bfcac4 --output build/medium-office-v4.json
```

Recovery requires the already locked OpenStudio 3.10 runtime and prototype/model
sources used by the preceding recovery; no EnergyPlus simulation is run.
The tracked [conversion artifact](../data/program-inputs/dhw-conversion-v1.json)
records exact source revisions, SHA-256 checksums, execution operands, selected
rating rows, original values/units, transformations and runtime/bridge hashes.

All **154 commercial channels** resolve: 114 main, 23 booster and 17 laundry.
Source gas efficiencies range from 0.78 to 0.82; electric conversion is 1.0.
All **41 residential heaters** retain their source burner/input conversion;
**40 fixtures** are included after the solar skip. This is a performance/source
census, not a claim that all 1,900 v4 exports have been generated or released.

The census checks 217 commercial service joins, 234 positive commercial leaf
draws and 95 included residential draw temperatures. **214 service recipes**
pass temperature feasibility; three SmallHotel service targets remain blocked,
as do their three leaf programs and potentially 12 mixtures containing them.
There are no additional unresolved joins in this census. Four complete export
pilots cover [Medium Office](examples/program-json-v4/medium-office.json),
[residential](examples/program-json-v4/residential.json),
[shared Large Office](examples/program-json-v4/shared-large-office.json) and
[mixed hotel](examples/program-json-v4/mixed-hotel.json).
Tests also cover staging, conservation, weather sensitivity, scaling, rejected
unknown performance, wrong heater assignment and duplicate demands.

[The coverage report](reviews/program-water-heating-coverage.json) enumerates
the blocked cases and **59 source services without an existing program
attachment** (31 main, 17 booster, 11 laundry). Their fuel/performance is recovered.
They remain independently owned source services; do not copy them into each
program or infer beneficiaries from heater location. Their eventual delivery
needs explicit consumer service assignment, or separately reviewed allocation.
This rollout preserves the existing program demand inventory.

## Remaining modeling decision: SmallHotel laundry

The 90.1-2007, 2013 and 2019 `Laundry_SmallHotel` main-loop space-type draws
request **82.222°C**, while their source main heater supplies **60°C**. The source
also creates an independent 82.222°C laundry loop with its own absolute draw.
The pinned `Standards.ServiceWaterHeating.rb` main-space helper passes these
space-type draws to the main loop. A laundry name is not sufficient evidence to
move that draw or replace/add the independent laundry demand.

EnergyPlus itself uses all hot flow when the requested target exceeds supply,
and its actual mixed temperature remains at the available hot temperature;
it warns about the unmet target. See the pinned
[WaterUse.cc implementation](https://github.com/NREL/EnergyPlus/blob/68a4a7c7744c380886913a92e061aba3d4a3fc54/src/EnergyPlus/WaterUse.cc#L942).
Its source checksum is recorded in the DHW evidence lock.

**Proposal:** add an explicit, source-bounded delivery policy for these three
cases: preserve the requested 82.222°C schedule, cap simplified delivered water
at the source main outlet of 60°C, and report unmet target temperature. This
preserves the source loop assignment. Reassigning to the laundry heater would
be a model correction with an additional demand-overlap review. Neither choice
is applied here; the three cases stay blocked pending the user's science decision.

**User comments / decision:**

<!-- Annotate the delivery policy or request the alternative assignment here. -->
