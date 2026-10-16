# Draw-only program water-heating implementation

User authorization: recover commercial conversion performance and implement the
simplified contract, using focused validation. ADR 0018 supplies the science scope.

1. Execute checksum-pinned Standards heater factory and efficiency methods on the
   nominal template/building/channel operands. Record successful ratings and any
   source lookup failures separately. Reuse the recovered residential burner
   efficiencies; never use EF/UEF directly as conversion efficiency.
2. Add Program JSON 4.0.0 as an opt-in exporter built from the unchanged v3
   defaulted export. Move each active water draw into a draw-only energy recipe;
   retain its demand identity, scaling, schedule and shared-service ownership.
   Embed fuel/performance evidence and separate main/booster temperature lifts.
   A consumer supplies weather-derived mains temperature and water fluid
   properties; the export contains no assumed density or heat capacity.
3. Reject unresolved joins/performance rather than guess. Explicitly skip the
   solar fixture. Retain raw v3 and detailed equipment data for every case.
4. Test source census/provenance and representative office, dwelling, staged,
   shared and mixed cases. Test physics and invalid-input rejection. Write pilot
   artifacts and migration instructions; do not build the website or regenerate
   the full unchanged program library. Review, audit, commit and push the branch.

Implementation rulings: v4 is a new opt-in consumer contract, not a replacement
release of v3. Water fluid properties are explicit simulation inputs, not new
Atlas defaults. Source lookup failure blocks energy export even if the source
factory leaves an initial efficiency on the heater.

Execution ledger:

- Recovery: 154/154 commercial channels source-resolved by pinned execution;
  reproduced byte-equivalent canonical data with `recover_dhw_conversion --check`.
- Contract/export: opt-in v4 and four source-backed pilots implemented. Existing
  v3 and detailed system source inputs were not edited. Scope metadata now names
  the excluded DHW distribution/loss/auxiliary effects explicitly.
- Census: 217 service joins, 234 positive commercial leaf draws and 95 residential
  draw temperature checks. Three SmallHotel source target/supply conflicts stay
  blocked, including 12 mixtures using their three leaf programs. A source-bounded
  delivery policy is proposed in the contract; no policy is assumed. Solar skip
  and 59 services requiring consumer attachment are enumerated separately.
- Test-first evidence: new module import failed before implementation; physical,
  contract and source cases then passed. Medium Office's expected fuel was
  corrected to the source prototype NaturalGas; the PRM baseline fuel-switch
  method is a separate workflow and was not invoked.
- Final independent review: one Important ownership/identity gap was reproduced.
  Regression tests failed for invented shared demand IDs, unrelated shared-service
  reassignment and omitted source water demands. Validation now compares complete
  recipes and water schedules against the program's unchanged v3 demand inventory;
  all three regressions pass. No critical source-recovery/science finding.
- Validation remains focused: water tests, existing aggregation/completeness
  regressions, schema, source execution and four-pilot/report reproduction. No
  site build, full unchanged program generation, simulation or lengthy CI.
- Final verification: 31 focused/regression tests passed;
  `recover_dhw_conversion --check` and `validate_program_water_heating --check`
  both passed after the review fix.

Approved delivery-cap follow-up (2026-10-12):

- User accepted capping delivery at the 60°C main outlet and reporting unmet
  target for the three SmallHotel laundry draws. Preserve requested 82.222°C
  schedules and source loop assignments; extend policy by demand origin to all
  12 dependent mixtures. No blanket cap or default performance is introduced.
- Initial new tests reproduced the original target/supply rejection in all three
  leaf cases and the six unresolved census entries. Added explicit delivery
  policy and diagnostic temperature/unmet-heat outputs; fuel includes delivered
  heat only. Full export checks cover all 15 affected programs.
- Keep the additive policy in the unreleased opt-in 4.0.0 draft. Add laundry and
  support-mixture examples and refresh only the focused coverage report.
- Verification: 34 focused/regression tests passed; six-pilot/report reproduction
  and complete validation of all 15 affected programs passed. The WaterUse source
  checksum matches the existing lock; its actual behavior locator is corrected
  to lines 1041-1136. No full catalogue/site generation or lengthy CI was run.
