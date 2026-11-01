# Generation settings

The schedule generator `atlas-schedules` {{ generator }} draws stochastic occupancy and use schedules from a
release's programs (ADR 0035, ADR 0051). What it needs beyond the program values is a folder's `generation.json`,
generation schema {{ generation_schema }}. Every folder page has a **Generation settings** section: the download,
each program's method and the parameters of each view, the building configurations and the services. Program pages
name their method and configurations in one line. A folder without generation settings says why; the
[coverage page](../coverage/index.md) counts them by reason.

## What the file holds

| Part | Holds |
| --- | --- |
| `programs` | One block per program the generator can draw: its `method` and, per view (`source`, and `filled` where the filled program generates differently), the view's parameters |
| `configurations` | The building configurations a `comstock_hours` view names: the sampling building type, the People (an occupancy schedule of the release and its design number of people) and whether rule days are inverted |
| `services` | The building services the generator draws, with the configurations they run under |

| Method | Parameters per view | Everything else from |
| --- | --- | --- |
| `comstock_hours` | `configuration_id` | the program's loads, controls and services |
| `composition` | none | the mix's members and their represented areas |
| `fixed` | none | the program's loads and schedules, as source rules |
| `resstock_unit` | the ResStock unit (ADR 0047) | the program's hot water; the request (zone, floor area, residents) |
| `resstock_dwelling` | the dwelling's executed OpenStudio-HPXML inputs | the dwelling record |

## Using it

The generator wheel bundles the generator view of its release; it reads release program IDs and a view
(`values: source | filled`):

```console
pip install atlas_schedules-{{ generator }}-py3-none-any.whl
atlas-schedules --version
```

The folder's `generation.json` in the site store is the release file's JSON in canonical form; the site index names
it per folder as `folders[<folder>].generation` ([site index](site-index.md)). BEMGen's *Schedule Draw* takes it as
its *Generator JSON*.
