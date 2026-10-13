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
`rho * cp * scaled_flow * max(delivery_target - mains, 0) / efficiency`, in W.
Normally `delivery_target = target`; the explicit approved policy below uses
`min(target, final_source_outlet)` instead.
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
The result includes `requested_temperature_degC`, `delivered_temperature_degC`,
`unmet_target_K` and `unmet_heat_W`, alongside `delivered_heat_W` and
`fuel_input_W`. Unmet heat is a diagnostic thermal demand, never charged to fuel.
Modeled delivery is `max(mains, delivery_target)`; this model supplies no cooling.
Unmet temperature is `max(requested - modeled_delivery, 0)`, and unmet heat is
`rho * cp * scaled_flow * unmet_temperature`. At zero flow both heat outputs are
zero; temperature outputs describe potential delivery, not a measured draw.

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
draws and 95 included residential draw temperatures. **217 service recipes**
pass, including three SmallHotel service targets with the approved delivery cap.
All three affected leaf programs and 12 dependent mixtures pass full export
validation. There are no unresolved joins or temperature cases in this census.
Six complete export
pilots cover [Medium Office](examples/program-json-v4/medium-office.json),
[residential](examples/program-json-v4/residential.json),
[shared Large Office](examples/program-json-v4/shared-large-office.json) and
[mixed hotel](examples/program-json-v4/mixed-hotel.json),
[SmallHotel laundry](examples/program-json-v4/small-hotel-laundry-2019.json) and
[its support mixture](examples/program-json-v4/small-hotel-support-2019.json).
Tests also cover staging, conservation, weather sensitivity, scaling, rejected
unknown performance, wrong heater assignment and duplicate demands.

[The coverage report](reviews/program-water-heating-coverage.json) enumerates
the approved capped cases and **59 source services without an existing program
attachment** (31 main, 17 booster, 11 laundry). Their fuel/performance is recovered.
They remain independently owned source services; do not copy them into each
program or infer beneficiaries from heater location. Their eventual delivery
needs explicit consumer service assignment, or separately reviewed allocation.
This rollout preserves the existing program demand inventory.

## Approved delivery policy: SmallHotel laundry

The 90.1-2007, 2013 and 2019 `Laundry_SmallHotel` main-loop space-type draws
request **82.222°C**, while their source main heater supplies **60°C**. The source
also creates an independent 82.222°C laundry loop with its own absolute draw.
The pinned `Standards.ServiceWaterHeating.rb` main-space helper passes these
space-type draws to the main loop. A laundry name is not sufficient evidence to
move that draw or replace/add the independent laundry demand.

EnergyPlus itself uses all hot flow when the requested target exceeds supply,
and its actual mixed temperature remains at the available hot temperature;
it warns about the unmet target. See the pinned
[WaterUse.cc implementation](https://github.com/NREL/EnergyPlus/blob/68a4a7c7744c380886913a92e061aba3d4a3fc54/src/EnergyPlus/WaterUse.cc#L1041).
Its source checksum is recorded in the DHW evidence lock.

**Accepted on 2026-10-12:** preserve the requested 82.222°C schedule, cap simplified
delivery at the source main outlet of 60°C, and report unmet target. Each of the
three affected recipes, including its occurrence in dependent mixtures, carries
`delivery_policy.method: cap_at_source_outlet`, `report_unmet_target: true`,
the ADR/user decision and pinned EnergyPlus evidence. This preserves source loop
assignment; it does not copy the independent laundry draw or invent a booster.

At mains temperature 10°C and consumer inputs of flow 0.001 m³/s, density
1000 kg/m³ and specific heat 4180 J/(kg·K), delivered heat is 209,000 W and
unmet heat is 92,888.889 W (22.222 K shortfall). Fuel input is delivered heat
divided by the recovered main-heater efficiency. These are illustrative consumer
inputs, not Atlas defaults. At mains above 60°C no heating or cooling is charged;
actual modeled delivery follows mains and the shortfall is computed accordingly.

The exporter assigns this policy only to the three approved source demands.
Validation rejects removal, alteration or assignment to unrelated demands.
Unapproved excessive targets still block export. This additive field completes
the unreleased opt-in 4.0.0 draft; published v3 is unaffected.

**User comments / decision:**

Accepted: "Cap delivery at 60°C and report unmet target (Recommended)".

<!-- Add further comments about consumer reporting here. -->
