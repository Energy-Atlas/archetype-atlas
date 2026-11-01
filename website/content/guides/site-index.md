# Site index for software

`site-manifest.json` at the site root is the machine-readable index of the catalogue (ADR 0052, ADR 0058). It
validates against the Draft 2020-12 schema
[`schemas/site-manifest.schema.json`](https://github.com/Energy-Atlas/archetype-atlas/blob/main/schemas/site-manifest.schema.json),
index schema `schema_version` 1.0.0, which the site check applies to every build. Read it once, then fetch only the
store files you need. Release {{ release }} is shown.

## Top level

| Key | Holds |
| --- | --- |
| `kind`, `schema_version` | `atlas_site` and the index's version |
| `release`, `release_manifest_sha256` | the release the site shows, and the SHA-256 of its `manifest.json` |
| `inputs_sha256`, `partial` | the build's input digest; `partial` is true for a sampled or partial build, which is never published |
| `programs` | every program by release ID |
| `construction_sets` | every construction set by ID, with its contexts |
| `folders` | every template × building type folder by its path, `<family>/<template>/<building type>/` |
| `counts`, `zoning` | totals, and the zoning recommendation pages |

## Programs

`programs[<id>]` holds `page`, the two exports `source` and `filled` as store paths, and `space_type`,
`building_type`, `folder` and `mode` (`source`, `department`, `general` or `dwelling`). Where `filled` is null,
`filled_reason` says why. `space_type` is the name before `_<building type>`, null for dwellings.

## Folders

`folders[<path>]` holds `family`, `template`, `building_type` (the slug), `programs` (its program IDs) and:

- `generation`: the store descriptor of the folder's `generation.json` ([generation settings](generation-settings.md)),
  or null with `generation_reason`, the class of folder that has none.
- `compositions`: every general and department mix of the folder, by its program ID:

  ```json
  "compositions": {
    "90-1-2013.primary-school.department.food-service-mixed.482be9": {
      "mode": "department",
      "members": [
        {"program_id": "90-1-2013.primary-school.source.cafeteria.4da2f7", "represented_area_m2": 315.0, "weight": 0.6521739130434783},
        {"program_id": "90-1-2013.primary-school.source.kitchen.c1d1dd", "represented_area_m2": 168.0, "weight": 0.34782608695652173}
      ]
    }
  }
  ```

  Each member is a source program of the same folder by its release ID; `represented_area_m2` is its floor area in
  the source prototype and `weight` its area share, the mix's default weight. The general mix (`General_Mixed`) holds
  every space type of the prototype; a department mix a group of them. A picker can list a folder's members with
  these default weights and let the user change them; the members' own programs are in `programs`. Folders without
  mixes have `{}`.

## Construction sets

`construction_sets[<id>].contexts[<key>]` holds `detailed` and `unified` as store paths. Where one document serves
both representations (the source model constructions of the code-prototype dwellings), `unified` names the same
file as `detailed`. Where a representation is missing, its path is null and `reason` (detailed) or
`unified_reason` says why.

## The store

Every export is a store file, `store/<sha256>.json.gz`, named by the SHA-256 of its gzip bytes. A descriptor (the
`generation` entries, and the pages' download buttons) also gives `size_bytes`, `decoded_size_bytes` and
`json_sha256`, the SHA-256 of the decompressed JSON. The JSON is canonical: keys sorted, no insignificant whitespace,
UTF-8 without `\u` escapes, numbers as Python's `json` writes them (shortest round trip, `1e-08`), no trailing
newline. To compare a file from elsewhere, hash its canonical form:

```console
python -m scripts.site_store export.json
```

GitHub Pages serves the site; it limits request rates, so fetch store files a few at a time and retry a refused
request after a pause.
