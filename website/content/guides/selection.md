# Select, inspect and copy

The catalogue shows the **latest release only**, release {{ release }}; its number is on every page. Older
releases stay as Git tags and release folders under `data/atlas-releases`. The [coverage page](../coverage/index.md)
counts what each family and template holds, and why an export or a generation setting is absent.

1. Open the [catalogue](../catalogue/index.md), choose a family (non residential or residential) and a template:
   each template has a one-line description and a link to its guide. The template's page lists its building types;
   a **folder page** lists that template × building type's programs, mixes, construction sets, generation settings,
   services, systems and water-reporting records.
2. Open a **program page**. Its facts name the template and building type as the downloads spell them, the folder's
   construction sets and the program's generation settings. Its sections show the **source export** under the
   download's own keys (`loads`, `controls`, `heat_fractions` …), then **Filled export**, every block the filled
   export changes, then **Release record**, the record's fillings with their rules and resolutions and the record
   values no export carries, then a mix's members, the schedules and the evidence. Every ID links to the object it
   names.
3. **Version.** The page without a query shows both exports. `?version=source` hides what the filled export changes
   and the fillings; `?version=filled` hides the source blocks the filled export replaces. A program with no filled
   export says why in its Filled export section, with or without JavaScript.
4. **Context.** Loads that vary by climate show one column per zone; `?climate=4A` dims the others. A **construction
   set page** lists its contexts (climate zone, and foundation, location or source reference where the set has
   them); `?climate=`, `?foundation=`, `?location=` and `?reference=` narrow the list. Climate labels are the atlas
   labels (`1A-tropical-semi-conditioned`); a zone (`1A`) selects every label in it.
5. **JSON.** Each export has **Copy** and **Download** buttons and names its release and the SHA-256 of the file
   Download saves. Both verify the stored document before decompressing it; Download saves its canonical bytes
   unchanged, Copy an indented rendering. Without JavaScript, **Download** saves the gzip file itself. The
   [Program JSON contract](program-json.md#checksums) defines the canonical form.
6. **Any ID.** The [viewer](../view/index.md) (`view/?id=…`) opens the page and anchor of any published ID
   (programs, schedules, resolved schedules, generation configurations), or shows the JSON of an evidence row or a
   resolution.

Geometry, sizing, zone assignment and stock weights remain the consumer's ([assign inputs to geometry](geometry.md)).
