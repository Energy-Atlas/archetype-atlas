# Card icons

`atlas_cards.py` extends the EnergyAtlas Wiki worked-example icon family supplied
by the `editorial-icons` skill. At the owner's request, the atlas's family/kind
cards use a house (Residential), office tower (Non Residential), three layers
(Constructions), and a three-blade circular fan (HVAC). Each has one blue accent
and uses the same seeded pen renderer as the existing guide and program icons.
Regular and bold SVGs live in `website/overrides/icons/`; the cards use regular.

The house silhouette is one continuous stroke from the foot of the left wall,
over the roof, to the foot of the right wall. It has no bottom edge; the blue
entrance is a separate accent. The house is reused on every Residential card
(there is no separate Dwelling overview card). Remaining subjects are a zoned
plan for Programs, overlapping sheets with a check for Selection and copying,
a calendar with a step profile for Schedule inspection, a folded JSON document
for Program JSON contract, and an open reference book for Library definitions.

Motion follows the live reference at <https://energy-atlas.github.io/quick-start/>:
animate individual SVG paths, once per hover/focus entry. The house doorway
hinges, office windows light in sequence, layers separate, fan blades turn within
a stationary housing, program dividers draw, copy sheets separate, the schedule
profile traces, JSON braces spread, and the reference book's page and ribbon move.
CSS path selectors use the drawing order above; preserve it when revising the
definitions. The overall SVG and oversized backdrop do not tilt. Reduced motion
disables these effects.

To reproduce with the installed skill (substitute your skill directory):

```powershell
python <editorial-icons>/scripts/ink_icons.py design/icons/atlas_cards.py --out build/card-icons house office layers fan program select-copy schedule json-document definitions
python <custom-icons>/scripts/validate_icon.py <SVG files> --require-matching-canvas
```

Copy the validated SVGs into `website/overrides/icons/`; keep `preview.html`
under ignored `build/`. Never edit the rendered path data by hand.

For the lightweight local site, run `python -m scripts.card_preview`, then
`python -m scripts.card_preview --serve`. This builds the current overview
markup with the real Material theme and all configured validation checks,
without producing catalogue data or record pages.
