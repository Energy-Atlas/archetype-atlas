# Unified construction site integration — local verification

Date: 2026-10-15. Branch: `feature/json-completion`.

## Cached-asset repair

The actual open in-app browser tab loaded current copy-only HTML together with
the old unversioned `construction.js`. That script still attached a handler to
the removed Download button and raised a null `addEventListener` error. Reference
selection never initialized and both copy controls stayed disabled. The old
cached stylesheet also omitted the new copy-button styling. Fresh browser
contexts had missed this warm-cache failure.

Generated first-party script/style URLs now carry a SHA-256-derived version.
The full delivery hook, standalone construction resources and focused renderer
share the same function; external assets and Material's existing hashed asset
names are unchanged. Changing asset bytes changes the URL; repeat rendering is
idempotent. No research or JSON semantics changed.

Two regression tests failed before the fix and now pass. All 26 focused asset,
HTML-delivery, construction site and refresh tests passed. The local rebuild
refreshed 177 pages / 3,320 contexts, generated zero program pages and zero new
JSON resources. Every construction page's script/style versions match served
bytes; all focused links passed.

The existing user tab was reloaded and directly checked: Medium Office reference
selection initializes, both copy dialogs complete with their respective copied
status, and the visible unified preview parses as schema 1.1.0 for the selected
context. Its repaired screenshot is the ignored local file
`build/unified-construction-cache-fixed.jpg`. The browser connector's clipboard
read returned an empty value, so this check does not claim an independent
clipboard-content comparison; frozen export parity remains covered by the
existing automated tests and earlier browser verification.

## Copy-only follow-up

The user requested copy actions for both representations instead of downloads.
The current page therefore has **Copy detailed JSON** and **Copy unified JSON**.
Each copies its named representation for the selected climate/reference,
independently of the preview selector. Source JSON and manual clipboard fallback
remain in the copy dialog. There is no construction download action. The initial
download checks below describe the earlier integration, before this UI revision.

The follow-up passed 19 focused site/refresh tests and the construction Node
tests. The browser regression checks both clipboard documents against their
frozen exports while the opposite representation is selected for preview.

## Initial integration

All 177 current construction definition pages offer separate Detailed (consumer
schema 2.0.0) and Unified (consumer schema 1.1.0) JSON for the same selected climate
and source reference. A representation selector controls preview, copy and
download. Filenames end in `-detailed.json` or `-unified.json`; neither file mixes
the representations. Original source JSON remains available in the copy dialog.

Unified data comes directly from the checksum-verified frozen 1.1.0 release.
The site performs no fitting, source recovery or program/schedule generation.
Packets share component sets and assemblies within each definition, load only
when requested, and retain bounded sizes and SHA-256 verification. All 3,320
contexts remain available in both representations. New unified delivery adds
2,833,276 compressed bytes across 177 packets; the largest decoded packet is
1,085,064 bytes, below the existing 16 MB bound. Supporting reference geometry
profiles are not duplicated into the site.

Detailed assemblies and assignment rules remain unchanged. Unified JSON retains
fit errors, mass-budget approximation flags and source overhang evidence; BEMGen
supplies actual geometry. The page distinguishes its original detailed resource
links from the equivalent assemblies in unified JSON. The contract guide links
the unified schema and standalone Medium Office/residential examples.

## Local verification

- 130 focused construction tests passed; after the button-class fix, the 19
  construction site/refresh tests passed again.
- All 24 existing Node tests passed, including construction selection and existing
  program/schedule behavior.
- Browser checks compared preview, clipboard and downloaded files against the
  corresponding frozen exports for Medium Office, Warehouse and residential
  examples. Both file types matched, including their selected context.
- No construction JSON packet loads on entry; each representation loads once
  when requested and subsequent preview/copy/download actions reuse it.
- Unsupported climates disable download. The client rejects missing equivalent
  assembly references. Representation URLs preserve climate/reference selection.
- Light and dark desktop screenshots and a 390 px mobile screenshot were
  inspected. Theme checks reload the compact page and assert its actual scheme.
  No mobile horizontal overflow or browser JavaScript errors were observed.
- Focused rendering refreshed 177 construction pages and the related guides and
  catalogue pages using the configured Markdown renderer and existing theme
  shells. All detailed/unified packets and original resources passed frozen
  equality, checksum, census and page-binding checks. Zero program pages were
  regenerated. A repeat refresh created zero new JSON resources.
- Links, assets and download descriptors passed on all 182 affected pages.
  The local site remains below the existing 1 GB publication-size ceiling.
- A separate read-only code review found no important findings. Visual review
  caught a shared `.definition-copy` handler on Download; a dedicated class and
  browser label assertion fixed and verified that conflict.

```powershell
.venv/Scripts/python.exe -m scripts.construction_site_refresh
.venv/Scripts/python.exe -m scripts.construction_site_smoke
```

Browser receipts and screenshots are ignored local artefacts at
`build/unified-construction-browser.json` and
`build/unified-construction-site-screenshots/`. The generated source/site trees
remain at `build/site-docs/` and `build/site/`.

The local Medium Office example is available at
<http://127.0.0.1:8765/archetype-atlas/definitions/construction-93cb2afe2fe44c8e084b9b99/?climate=3B&reference=90.1-2019%2FMediumOffice&representation=unified>.

No full MkDocs/program/schedule build, push, workflow dispatch, CI/CD or Pages
deployment ran. Historical research releases and source data are unchanged.
