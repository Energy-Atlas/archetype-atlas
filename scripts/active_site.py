"""Fresh current-only catalogue build; no history restoration or legacy routes."""
import argparse
import shutil
import tempfile
from pathlib import Path

from scripts.common import ROOT, load_json
from scripts.definition_contract import canonical, TABLES
from scripts.definition_release import read_bundle, verify
from scripts.definition_site import generate, write
from scripts.object_site import generate_objects


def generate_active_site(bundle, target, publish=True):
    target = Path(target).resolve()
    if target in {ROOT.resolve(), (ROOT / 'build').resolve()} or (target.is_relative_to(ROOT) and not target.is_relative_to(ROOT / 'build')):
        raise ValueError('Refuse to replace repository sources or build root')
    if target.exists() and target.is_relative_to(ROOT / 'build') and any(target.iterdir()) and not (target / 'site-manifest.json').is_file():
        raise ValueError('Existing output must be marked as generated')
    if not target.is_relative_to(ROOT / 'build'):
        # Temporary test output is safe only when not replacing an existing tree.
        if target.exists() and any(target.iterdir()): raise ValueError('Refuse to replace output outside workspace build')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        stage = Path(temporary) / 'docs';stage.mkdir()
        shutil.copytree(ROOT / 'website/assets', stage / 'assets')
        if publish:
            from scripts.site_assets import fetch_assets, verify_asset
            vendor = fetch_assets()
            for item in load_json(ROOT / 'website/assets.lock.json')['assets']:
                destination = stage / 'assets/vendor' / item['path'];destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(verify_asset(vendor, item), destination)
        generate(bundle, stage, publish=False, pages=False)
        if publish:
            from scripts.query_v2 import generate_delivery
            generate_delivery(bundle, stage / 'delivery/v2')
        result = generate_objects(bundle, stage)
        result['counts'] = {table: len(bundle[table]) for table in TABLES}
        write(stage, 'index.md', landing(bundle))
        write(stage, 'guides/selection.md', '# Select, inspect and copy\n\nChoose a building family and object kind in the [catalogue](../catalogue.md). '
              'Filter by building type, vintage, climate where relevant, and program detail or system type.\n\n'
              'Follow a load schedule, construction material or system component to its dedicated page. '
              'Expand **JSON** to inspect the complete object. **Copy JSON** opens the copy choices.\n\n'
              'Programs offer raw JSON and, when all active inputs resolve, ready JSON with source recovery and approved defaults, including every referenced schedule. '
              'Source unknowns remain visible as Unknown. Geometry, model sizing and service host assignment remain consumer responsibilities. '
              'Constructions offer source-ready JSON v2 after climate/reference selection, with complete component and material/provenance closure. '
              '[Construction contract](construction-json.md). HVAC objects retain exact source JSON and explicit unresolved inputs.\n\n'
              '[Program connector contract](program-json.md) · [Default policy](../contracts/program-json-defaults-v2.json)\n')
        write(stage, 'guides/schedules.md', '# Inspect schedules\n\nOpen a schedule from a program, construction or system reference. '
              'Load its interactive plots to see unique day profiles and a day-of-year × hour-of-day heatmap. '
              'Hover for exact values and click a heatmap day to inspect its step profile.\n\n'
              'Rule sets use an explicit calendar year (preview default 2007), with optional explicit holiday dates. '
              'The last matching specific source rule wins, then the last Default fallback. '
              'Wrapped seasons, holidays and separate design days retain their source meaning. Unknown coverage remains a gap.\n\n'
              'Annual realizations retain their recorded year and hourly interval convention, with no DST or holiday overrides. '
              'No stochastic schedule generation or calendar transplantation occurs. '
              'Tables remain available if chart rendering fails.\n\n'
              'Plots use locally served [Plotly cartesian 3.1.0](https://github.com/plotly/plotly.js/blob/v3.1.0/dist/README.md#plotlyjs-cartesian).\n')
        contract = (ROOT / 'docs/program-json-v3-contract.md').read_text(encoding='utf-8')
        contract = contract.replace('../schemas/', '../contracts/').replace('../sources/', '../contracts/').replace('examples/program-json-v3/', '../examples/')
        contract = contract.replace('reviews/program-json-remaining-decisions.md', 'program-json-remaining-decisions.md')
        write(stage, 'guides/program-json.md', contract)
        write(stage, 'guides/program-json-remaining-decisions.md', (ROOT / 'docs/reviews/program-json-remaining-decisions.md').read_text(encoding='utf-8'))
        from scripts.construction_site import library_guide,program_presentation_inputs
        write(stage, 'guides/definitions.md', library_guide())
        result['program_presentation_inputs']=program_presentation_inputs(bundle)
        for src in (ROOT / 'schemas/program-json-v3.schema.json', ROOT / 'schemas/schedule-json-v2.schema.json', ROOT / 'sources/program-json-defaults-v2.json'):
            (stage / 'contracts').mkdir(exist_ok=True);shutil.copyfile(src, stage / 'contracts' / src.name)
        shutil.copytree(ROOT / 'docs/examples/program-json-v3', stage / 'examples')
        from scripts.construction_site import generate_constructions,install_contract,projection
        from scripts.construction_distribution import load_current_release as load_release
        construction_ids=set(load_json(ROOT/'data/construction-releases/v2.0.0/index.json')['construction_sets'])
        has_constructions=construction_ids <= {r['id'] for r in bundle['constructions']}
        if has_constructions:
            frozen_constructions=load_release()
            construction=generate_constructions(frozen_constructions,bundle,stage)
            result['objects']=len(load_json(stage/'object-index.json'))
            result['counts']['constructions']=construction['definitions']
            result['construction_v2']={k:construction[k] for k in ('construction_schema','definitions','contexts')}
            write(stage,'index.md',landing(projection(frozen_constructions,bundle)))
        install_contract(stage,include_resources=has_constructions)
        notices = stage / 'notices';notices.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / 'LICENSE', notices / 'original-work.txt')
        links = ['[Original-work notice](notices/original-work.txt)']
        for source in (ROOT / 'data/definition-releases/v0.1.1/sources/licenses').glob('*.txt'):
            shutil.copyfile(source, notices / source.name);links.append(f'[{source.stem}](notices/{source.name})')
        write(stage, 'sources.md', '# Sources and notices\n\nThe active library derives from checksum-locked OpenStudio Standards, DOE/PNNL, ComStock and ResStock evidence. '
              'Code/prototype and existing-stock contexts remain distinct. '
              'Object JSON retains source IDs, field locators, original values and transformations. '
              'Experimental defaults are labelled separately.\n\n' + '\n\n'.join(links) + '\n\n'
              'Hospital ER_Triage equipment recovery also uses Deru, Michael, et al., '
              '*Commercial Reference Building: Hospital*, National Renewable Energy Laboratory, 25 November 2014, '
              '[OEDI submission 157](https://data.openei.org/submissions/157), '
              'under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). '
              'The post-1980 v1.3_5.0 SI scorecard supplies the recovered magnitude; the pinned standards schedule '
              'and heat fractions are retained. The copied program metadata records the exact cell, checksum and transformation.\n\n'
              '[Plotly MIT license](assets/vendor/plotly-LICENSE.txt)\n\n'
              'Site fonts, SIL Open Font License 1.1: [Geist](assets/fonts/OFL-Geist.txt) · [Geist Mono](assets/fonts/OFL-GeistMono.txt) · '
              '[Cormorant Garamond](assets/fonts/OFL-CormorantGaramond.txt)\n\nOriginal work is unlicensed by user choice; upstream notices continue to apply.\n')
        write(stage, 'site-manifest.json', canonical(result).decode())
        if target.exists(): shutil.rmtree(target)
        from scripts.site import rename_generated
        rename_generated(stage,target)
    return result


def landing(bundle):
    """Landing page: a hero, then numbered strips over shared-border grids (design/ui-design-spec.md, section 0.7)."""
    counts = (f'{len(bundle["programs"]):,} programs · {len(bundle["constructions"]):,} constructions · '
              f'{len(bundle["hvac_systems"]):,} HVAC systems')
    return ('---\nhide:\n  - navigation\n  - toc\n---\n\n'
            '<div class="ea-hero" markdown>\n\n'
            '# Deterministic energy definitions<br>*for zoning experiments.* { #energy-archetype-atlas }\n\n'
            'Choose Residential or Non Residential, then Programs, Constructions or HVAC systems. '
            'Inspect linked schedules, materials and components, and copy complete JSON.\n\n'
            f'{counts}\n{{ .ea-hero__meta }}\n\n'
            '[Open the catalogue](catalogue.md){ .md-button .md-button--primary }\n\n'
            '</div>\n\n'
            '## Catalogue { .ea-strip data-index="01" data-note="Two building families" }\n\n'
            '<div class="grid cards icon-cards" markdown>\n\n'
            '-   <span class="ea-card-icon" data-icon="house"></span>[Residential](catalogue/residential/index.md)\n\n'
            '    Browse programs, constructions and HVAC systems.\n\n'
            '-   <span class="ea-card-icon" data-icon="office"></span>[Non Residential](catalogue/nonresidential/index.md)\n\n'
            '    Browse programs, constructions and HVAC systems.\n\n'
            '</div>\n\n'
            '## How to use { .ea-strip data-index="02" data-note="Four guides" }\n\n'
            '<div class="grid cards compact icon-cards" markdown>\n\n'
            '1.  <span class="ea-card-icon" data-icon="select-copy"></span>[Selection and copying](guides/selection.md)\n\n'
            '    Choose a family and object kind, filter, inspect linked objects, and copy JSON.\n\n'
            '2.  <span class="ea-card-icon" data-icon="schedule"></span>[Schedule inspection](guides/schedules.md)\n\n'
            '    Unique day profiles, an annual day × hour heatmap, and exact tables.\n\n'
            '3.  <span class="ea-card-icon" data-icon="json-document"></span>[Program JSON contract](guides/program-json.md)\n\n'
            '    The self-contained raw and default-filled program form.\n\n'
            '4.  <span class="ea-card-icon" data-icon="definitions"></span>[Library definitions](guides/definitions.md)\n\n'
            '    What programs, constructions and HVAC definitions supply.\n\n'
            '</div>\n\n'
            '## Sources { .ea-strip data-index="03" data-note="Notices" }\n\n'
            'The library derives from checksum-locked OpenStudio Standards, DOE/PNNL, ComStock and ResStock evidence. '
            'Upstream notices continue to apply.\n\n'
            '[Sources and notices](sources.md){ .md-button }\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--definitions', type=Path, default=ROOT / 'data/definition-releases/v0.1.1')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/site-docs')
    parser.add_argument('--reuse-existing',action='store_true',help='Local construction overlay on a marked generated tree; refresh only stale program presentation')
    args = parser.parse_args()
    report = verify(args.definitions)
    if report.errors: raise SystemExit('; '.join(report.errors[:5]))
    bundle=read_bundle(args.definitions)
    if args.reuse_existing:
        from scripts.construction_site import integrate_existing
        report=integrate_existing(bundle,args.output)
        print(f"Construction site: {report['definitions']} sets, {report['contexts']} contexts, {len(report['resources']['assemblies'])} assemblies")
    else:print(canonical(generate_active_site(bundle, args.output)).decode())


if __name__ == '__main__': main()
