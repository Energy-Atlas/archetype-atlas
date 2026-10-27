# Library definitions

A release folder holds one template × building type; the catalogue mirrors it.

- **Programs** (`source`, `department`, `general`; `dwelling` for residential): loads,
  controls, conditioning and ventilation per program, with fillings in place and
  unresolved fields as explicit nulls. Department and general mixes list their members
  and area shares; their members are programs of the same folder.
- **Construction sets**: one suite per set, with a context per climate zone and, where
  the set covers several, per source reference, foundation or location.
- **Folder records**: building services (hot water and other building-level loads),
  HVAC systems and their components, and water-reporting records. HVAC parameters stay
  unresolved where the source does not state them.
- **Template library**: assemblies, materials and performance rules shared by the
  template's building types.
- **Evidence**: every value cites an evidence row (source locator, original value and
  unit, transformation, interpretation). Shared texts are in the
  [evidence glossary](../catalogue/glossary/index.md).

The atlas supplies energy semantics, not geometry, sizing or stock weights.
