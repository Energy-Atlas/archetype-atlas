# Program JSON contract

Every program page offers the two consumer exports of release {{ release }}, read straight from the release by
`scripts.atlas_exports`, as Program JSON {{ schema:program }}:

- **source**: actual values only, as the source states them, including values the source implies as zero. Unknowns
  stay null with their reason.
- **filled**: actual values plus fillings and approved defaults, each filling recorded in `metadata.resolutions`
  with its rule and decision, and draw-only water heating. This is the version BEMGen consumes. Mixes are split into
  their members' loads; holiday rules are added to schedules that lack them (`resolved-schedule-…`).

The program page shows the source export under the download's own keys, then a **Filled export** section with
every block the filled export changes, then the release record's fillings and the record values no export carries.
`?version=source` and `?version=filled` hide the other export's blocks.

The major is 5; each data release added optional fields as a minor: 5.1.0 (DOE reference reconciliation:
fenestration, source calendar, alternates, building services), 5.2.0 (IECC commercial: loads and schedules by
climate, source zones), 5.3.0 (dwelling programs) and 5.4.0 (lighting controls, ADR 0044). A later minor's optional
blocks render on the program page without a site change. IECC commercial, IECC residential and manufactured-housing
programs export the source version only until their water heaters are stored; the
[coverage page](../coverage/index.md) counts them with the reason.

Contracts and schemas: [consumer contracts of release 1.0.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/consumer-contracts-release-1.0.0.md),
[release 1.1.0](https://github.com/Energy-Atlas/archetype-atlas/blob/main/docs/consumer-contracts-release-1.1.0.md),
the release notes of each data release in [`docs/`](https://github.com/Energy-Atlas/archetype-atlas/tree/main/docs), and the
schemas in [`schemas/`](https://github.com/Energy-Atlas/archetype-atlas/blob/main/schemas). The exporter reads
releases {{ releases }}:

```console
python -m scripts.atlas_exports --release {{ release }} --program ID --version filled
```

## Checksums

Each download names its release and the SHA-256 of the JSON file it saves. The file is the store's canonical JSON:
keys sorted, no insignificant whitespace, UTF-8 without `\u` escapes, numbers as Python writes them, no trailing
newline (`json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))`). The same JSON in any
layout, such as the exporter's indented output, has the same canonical SHA-256:

```console
python -m scripts.site_store program.json
```

Without JavaScript, **Download** saves the gzip file itself, named by the SHA-256 of its gzip bytes; decompressed,
it is the canonical file. The [site index guide](site-index.md) describes the store.
