# Construction weighting support profiles 1.0.0

Program-library supporting data, separate from program loads and schedules.
129 commercial source references and 41 residential source fixtures; 1,158 native
commercial program keys. Existing program definition links are exact source-key
joins, not assertions that every recovered key has a published load contract.

Default weighting uses precomputed source geometry only. Counted source floor
shares, conditional native-building/program group shares, net component exposure,
volume, story scopes and physical mass inventories retain their denominators.
Non-counted scopes use direct exposure. Apply source multipliers once.
Window-operation areas are separated by exterior/interior semantic.

Surface-pair inventories preserve both original face operands. A pair with unequal
multipliers has unknown physical area under the default require_equal policy;
it is not resolved by whichever face is encountered first. The proposed symmetric
mean policy requires an explicit user decision. Profiles retain evidence while
corresponding derived mass semantics are blocked.

python -m scripts.construction_weighting --check compares normalized cached source
recovery and manifest bytes. Add --recover to rerun the pinned geometry/mass
methods, using the existing locked source/runtime retrieval described by the
construction recovery tooling. No HVAC, annual schedules or site build is run.
load_profiles() validates checksums before use. Native source revisions, archive
and executable checksums are retained in manifest.json; field source locators
and original operands/units are in profiles.json and linked immutable inputs.

Preserve LICENSE and sources/licenses upstream notices. Original Atlas work
remains unlicensed by user choice. No production publication is implied.
