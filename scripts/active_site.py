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
              'Programs offer raw JSON or JSON with explicit experimental defaults, including every referenced schedule. '
              'Source unknowns remain visible as Unknown. Geometry, model sizing and service host assignment remain consumer responsibilities. '
              'Other library objects expose their exact raw JSON; unresolved physical inputs stay explicit.\n\n'
              '[Program connector contract](program-json.md) · [Default policy](../contracts/program-json-defaults.json)\n')
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
        contract = (ROOT / 'docs/program-json-v2-contract.md').read_text(encoding='utf-8')
        contract = contract.replace('../schemas/', '../contracts/').replace('../sources/', '../contracts/').replace('examples/program-json-v2/', '../examples/')
        contract = contract.replace('Prepared on `feature/dto-json-v2`; not yet emitted by the website.', 'The catalogue emits this self-contained program contract.')
        contract = contract.replace('The atlas exporter will apply the policy before producing this form.', 'The atlas exporter applies the policy before producing this form.')
        write(stage, 'guides/program-json.md', contract)
        write(stage, 'guides/definitions.md', '# Library definitions\n\nPrograms supply loads and determined schedules. Constructions supply element properties and separately scoped air exchange. '
              'HVAC definitions supply fixed component performance and explicit conditional requirements. '
              'Compare corresponding elements; unknown inputs do not establish identity.\n\n'
              '[Program JSON contract](program-json.md) · [Sources](../sources.md)\n')
        for src in (ROOT / 'schemas/program-json-v2.schema.json', ROOT / 'schemas/schedule-json-v2.schema.json', ROOT / 'sources/program-json-defaults.json'):
            (stage / 'contracts').mkdir(exist_ok=True);shutil.copyfile(src, stage / 'contracts' / src.name)
        shutil.copytree(ROOT / 'docs/examples/program-json-v2', stage / 'examples')
        notices = stage / 'notices';notices.mkdir()
        shutil.copyfile(ROOT / 'LICENSE', notices / 'original-work.txt')
        links = ['[Original-work notice](notices/original-work.txt)']
        for source in (ROOT / 'data/definition-releases/v0.1.1/sources/licenses').glob('*.txt'):
            shutil.copyfile(source, notices / source.name);links.append(f'[{source.stem}](notices/{source.name})')
        write(stage, 'sources.md', '# Sources and notices\n\nThe active library derives from checksum-locked OpenStudio Standards, DOE/PNNL, ComStock and ResStock evidence. '
              'Code/prototype and existing-stock contexts remain distinct. '
              'Object JSON retains source IDs, field locators, original values and transformations. '
              'Experimental defaults are labelled separately.\n\n' + '\n\n'.join(links) + '\n\n'
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
            '<div class="grid cards" markdown>\n\n'
            '-   [Residential](catalogue/residential/index.md)\n\n'
            '    Browse programs, constructions and HVAC systems.\n\n'
            '-   [Non Residential](catalogue/nonresidential/index.md)\n\n'
            '    Browse programs, constructions and HVAC systems.\n\n'
            '</div>\n\n'
            '## How to use { .ea-strip data-index="02" data-note="Four guides" }\n\n'
            '<div class="grid cards compact" markdown>\n\n'
            '1.  [Selection and copying](guides/selection.md)\n\n'
            '    Choose a family and object kind, filter, inspect linked objects, and copy JSON.\n\n'
            '2.  [Schedule inspection](guides/schedules.md)\n\n'
            '    Unique day profiles, an annual day × hour heatmap, and exact tables.\n\n'
            '3.  [Program JSON contract](guides/program-json.md)\n\n'
            '    The self-contained raw and default-filled program form.\n\n'
            '4.  [Library definitions](guides/definitions.md)\n\n'
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
    args = parser.parse_args()
    report = verify(args.definitions)
    if report.errors: raise SystemExit('; '.join(report.errors[:5]))
    print(canonical(generate_active_site(read_bundle(args.definitions), args.output)).decode())


if __name__ == '__main__': main()
