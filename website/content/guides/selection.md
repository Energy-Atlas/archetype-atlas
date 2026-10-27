# Select, inspect and copy

The catalogue shows the **latest release only**; its number is on every page. Older
releases stay as Git tags and release folders under `data/atlas-releases`.

1. Open the [catalogue](../catalogue/index.md), choose a family (non residential or
   residential), a template and a building type. The folder page lists that
   template × building type's programs, mixes, construction sets, services, systems and
   water-reporting records.
2. Open a **program page**. Its overview, loads, parameters and any other blocks of the
   record render in place, with the schedules it uses and the evidence it cites further
   down. Every ID links to the object it names.
3. **Version.** Fillings (researcher assumptions and values from executed upstream code)
   sit on the field they fill, marked in colour. Add `?version=source` to hide them or
   `?version=filled` to highlight them; the page without a query shows both. Families
   that export the source version only (IECC commercial and residential, manufactured
   housing) say why when `?version=filled` is asked for, and show the source.
4. **Context.** Loads that vary by climate show one column per zone; `?climate=4A`
   dims the others. A **construction set page** lists its contexts (climate zone, and
   foundation, location or source reference where the set has them); `?climate=`,
   `?foundation=`, `?location=` and `?reference=` narrow the list. Climate labels are
   the atlas labels (`1A-tropical-semi-conditioned`); a zone (`1A`) selects every label
   in it.
5. **JSON.** Each export has **Copy** and **Download** buttons. Both verify the stored
   document's SHA-256 before decompressing it. Without JavaScript, **Download** saves the
   gzip file itself.
6. **Any ID.** The [viewer](../view/index.md) (`view/?id=…`) opens the page and anchor of
   any published ID, or shows the JSON of an evidence row.

Geometry, sizing, zone assignment and stock weights remain the consumer's.
