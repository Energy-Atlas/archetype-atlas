# Definition library v0.1.1 coverage

Canonical definition schema 1.0.0; selective delivery schema 2.0.0.

| Kind | Records | Assumed | Known top-level parameters | Unknown top-level parameters |
|---|---:|---:|---:|---:|
| constructions | 3798 | 4 | 2997 | 8946 |
| hvac_systems | 1046 | 0 | 41 | 4020 |
| programs | 1900 | 0 | 5326 | 417 |

These field counts exclude nested load and component parameters. Coverage is not
simulation readiness. All 768 commercial source programs, 2,451 envelope targets
and 1,145 system descriptors are represented or explicitly classified in
coverage.json; 140 ancillary equipment descriptors remain supporting resources.

All 17 commercial families and 83 exact building/template contexts retain source
leaves. Approved mixtures use unrounded source represented areas; supported
department/general modes and unchanged leaves are explicit. Basement and attic
variants never enter mix denominators. Forty-one ResStock fixtures remain
independent whole-dwelling definitions, separate from Standards apartments.

Known limitations:

- All commercial source infiltration rates are unknown. The 48 positive minimum
  total-air-change requirements belong to Outpatient; outdoor air and total
  supply remain separate. Construction-set space selectors constrain applicability.
- Conditional HVAC ratings preserve capacity bands, dates, technology predicates
  and metric names. Fan curves, controls and exact rule assignment remain
  unresolved where source descriptors cannot establish them. No scalar COP or
  sizing is invented. Compare corresponding known component properties only.
- Conflicting assembly names are unresolved rather than resolved by row order.
  Original layers, SI conversions, films and target adjustments retain evidence.
  F/C ground targets need consumer geometry and a ground heat-transfer model.
- Only four internal/ground fallback definitions are assumed; use them only
  where source assignments cannot be resolved. No infiltration or load defaults
  were introduced. Shared conditioning categories are independent of browse gates.
- Residential profiles are determined 2007 realizations, with original seed,
  station-proxy weather and nominal setpoint limitations. They are not portable
  calendars without an explicit adapter. Magnitudes and absent channels remain
  unknown; three vacant fixtures export occupancy only. No room-area mix is
  required for a whole dwelling. ACH50 is a pressure-test rate, not natural ACH.
- Shared services are instantiated once by demand/service identity. A reporting
  allocation or reference does not add a second physical draw.

Reproduce with `python -m scripts.definition_release --verify` and
`python -m scripts.definition_release --reproduce`. Release manifests pin every
canonical table, schema, lock, policy, inspection export and notice.
