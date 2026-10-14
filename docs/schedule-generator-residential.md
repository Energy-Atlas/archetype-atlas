# Residential generator R1

[v0.2.0](../data/generator-releases/v0.2.0/manifest.json) supplies all 41 actual
ResStock source fixtures, using their exact physical inputs and 37 checksum-locked
station proxies. Its [coverage report](validation/schedule-generator-coverage-residential.json)
closes all 766 channels: 415 generated and 351 source-fixed. The
[scope](../sources/schedule-generator-residential-scope.json) enumerates every
fixture, template, region and weather binding; the
[inspection matrix](../data/schedule-generator/families/residential/channel-matrix.csv)
retains separate fuel, host and basis demands.

Download [generator.zip](../data/generator-releases/v0.2.0/generator.zip), extract
`references/all-cases-request.json`, and run it with Python 3.11 or later:

```text
python -I -S generator.zip --request all-cases-request.json --output bundle.json
```

The request contains every required source operand and resource identity
`resources-82019ccd24b679a968d35e5e7f2d7575dd3aa4ba99c69dd6e2b9b45b09b54612`.
Generation needs only Python's standard library and the ZIP, with no checkout,
network, native simulator or external library. `references/all-cases-bundle.json.gz`
is its complete numerical reference; `python -I -S generator.zip --reproduce`
runs the artifact's own runtime and source/discrete/numerical comparison policy.

The explicit year is 2007, with 8,760 local-standard hourly intervals and no
holiday or implicit DST adjustment. Each selected fixture retains its actual
residents, bedrooms, installed end uses, coordinates, state, UTC offset, weather
and thermostat arguments. Change the explicit unsigned 64-bit master seed for a
new realization. Instance order controls native cumulative-factorial unit seed
allocation; removing or inserting an instance can change later unit seeds.

Original annual energy and water-volume targets are conserved by adjusting
effective magnitude after generation. That amplitude is not installed/nameplate
capacity. Counts, activity, temperature controls and source-fixed companions
retain their source semantics. Zero occupants preserve the native stochastic skip
and explicit zero occupancy; positive fixed loads remain. EV and HVAC equipment
unavailability overlays remain excluded. Station proxies remain distinct from
the unavailable original county EPWs.

R1 is an intermediate residential-only milestone. M1's independent commercial
pilot and its immutable v0.1.0/v0.1.1 artifacts remain available. A subsequent
cumulative resource set must prove generated and bound mixed-family constituents
before advertising composition across these completed families. All remaining
1,859 commercial programme identities and 378 catalogue compositions remain
outside R1. This release does not claim full extraction or ComStock population
realization equivalence.
