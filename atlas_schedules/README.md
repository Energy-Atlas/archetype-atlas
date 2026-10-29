# atlas-schedules

Stochastic hourly schedules for the programs of the Energy Archetype Atlas: a readable
port of ComStock's hours-of-operation sampling and ResStock's occupant and appliance
schedules (ADR 0035), driven by the generation parameters that atlas release 2.1.0
publishes with its programs (ADR 0049).

The package holds the code, the request schema and the generator-wide data (ComStock
sampling tables, ResStock characteristics and schedule tables, TMY3 weather, upstream
notices). It holds no copy of the atlas's program values: it reads them from a release.

## Install and point it at a release

```bash
pip install atlas_schedules-3.0.0-py3-none-any.whl
```

Download `atlas-release-2.1.0.zip` from the atlas's `v2.1.0` GitHub release, check it
against that release's `SHA256SUMS`, and extract it. The folder holds `v2.0.0/` and
`v2.1.0/` side by side. Then name it:

```bash
export ATLAS_RELEASES=/path/to/extracted/folder
```

or call `atlas_schedules.release.set_releases(path)`. Run from the atlas source tree,
the generator reads `data/atlas-releases` without either.

## Generate

```bash
atlas-schedules request.json -o bundle.json
```

A request (schema 3.0.0) names each program by its atlas release ID and, optionally, its
view: `"values": "source"` (actual values) or `"filled"` (actual values and fillings).
The default is `filled` where the program has that view. Definition IDs (`program-…`,
`service-…`) translate through the release's `definition-map.json`
(`atlas_schedules.release.translate`). Every bundle records the generator version and the
release version and manifest hash it read.

## Licences

Original code is MIT and original data CC BY 4.0 (attribute "Archetype Atlas,
Energy-Atlas" with the release number). Third-party data and ported code keep their
upstream licences: see `atlas_schedules/data/notices/`. This is not an official
OpenStudio(R), DOE, PNNL, ComStock or ResStock product.
