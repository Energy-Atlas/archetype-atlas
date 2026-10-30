"""Suite site (ADR 0043): store, generic rendering, page layout, search and checks."""
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import site_check, site_release, site_store
from scripts.site_pages import context_facets, markdown, split_shared
from scripts.site_render import Links, Page, annual_summary, plot, render, schedule, zone


def links(**pages):
    out = Links()
    for identifier, url in pages.items():
        out.place(identifier, url)
    return out


class StoreTests(unittest.TestCase):
    def test_documents_are_content_addressed_deterministic_and_shared(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = site_store.Store(temporary)
            first = store.put({'b': 1, 'a': [1.5, None]})
            again = store.put({'a': [1.5, None], 'b': 1})
            self.assertEqual(first, again)
            self.assertEqual(len(store.files), 1)
            data = (Path(temporary)/first['href']).read_bytes()
            self.assertEqual(first['sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(json.loads(gzip.decompress(data)), {'a': [1.5, None], 'b': 1})
            self.assertEqual(site_store.read(temporary, first), {'a': [1.5, None], 'b': 1})

    def test_a_changed_file_fails_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = site_store.Store(temporary)
            descriptor = store.put({'a': 1})
            (Path(temporary)/descriptor['href']).write_bytes(gzip.compress(b'{"a":2}', mtime=0))
            with self.assertRaises(ValueError):
                site_store.read(temporary, descriptor)

    def test_packets_stay_under_the_bound_and_name_their_first_key(self):
        rows = {f'id-{i:05d}': {'page': 'catalogue/x/'+'y'*40, 'anchor': f'id-{i:05d}'} for i in range(4000)}
        rows['id-big'] = {'object': 'z'*200_000}
        with tempfile.TemporaryDirectory() as temporary:
            store = site_store.Store(temporary)
            packets, firsts = store.packets(rows)
            self.assertEqual(len(packets), len(firsts))
            seen = {}
            for descriptor, first in zip(packets, firsts):
                value = site_store.read(temporary, descriptor)
                self.assertEqual(min(value), first)
                if 'id-big' not in value:
                    self.assertLessEqual(descriptor['decoded_size_bytes'], site_store.PACKET)
                seen.update(value)
            self.assertEqual(seen, rows)
            self.assertEqual(firsts, sorted(firsts))


class RenderTests(unittest.TestCase):
    def test_nulls_stay_explicit_and_zero_is_a_value(self):
        html = render({'value': None, 'zero': 0}, Page(Links(), 'catalogue/a/'))
        self.assertIn('<span class="ea-null">null</span>', html)
        self.assertIn('<dd>0</dd>', html)

    def test_ids_link_to_the_local_anchor_their_page_or_the_viewer(self):
        site = links(**{'90-1-2019.office.lighting.abc123': 'catalogue/c/90-1-2019/office/programs/source/x/'})
        site.viewer.add('evidence-0123456789')
        page = Page(site, 'catalogue/c/90-1-2019/office/programs/source/y/')
        page.local.add('local-schedule-id')
        html = render(['90-1-2019.office.lighting.abc123', 'evidence-0123456789', 'local-schedule-id', 'plain text'], page)
        self.assertIn('href="../x/#90-1-2019.office.lighting.abc123"', html)
        self.assertIn('href="../../../../../../../view/?id=evidence-0123456789"', html)
        self.assertNotIn('href="#local-schedule-id"', html)
        site.place('local-schedule-id', page.url)
        self.assertIn('href="#local-schedule-id"', render('local-schedule-id', page))
        self.assertIn('plain text', html)

    def test_an_unknown_optional_block_renders_without_code_changes(self):
        block = {'lighting_controls': {'daylighting': [{'zone_fraction': 0.25, 'setpoint_lux': 500, 'area': 'geometry_dependent'}],
                                       'occupancy_sensors': None}}
        html = render(block, Page(Links(), 'catalogue/a/'))
        for text in ('lighting_controls', 'daylighting', 'zone_fraction', '0.25', '500', 'geometry_dependent', 'occupancy_sensors'):
            self.assertIn(text, html)
        self.assertIn('<table>', html)

    def test_fillings_are_marked_in_place(self):
        html = render({'loads': [{'quantity': 'occupancy', 'value': None, 'filling': {'rules': ['r'], 'set': {'value': 0}}}]},
                      Page(Links(), 'catalogue/a/'))
        self.assertIn('<td class="ea-filling">', html)
        html = render({'status': 'unknown', 'filling': {'set': {'value': 0}}}, Page(Links(), 'catalogue/a/'))
        self.assertIn('<dd class="ea-filling">', html)

    def test_values_by_climate_carry_their_zone(self):
        html = render({'value_by_climate': {'1A': 1.0, '4A': 2.0, '7': 3.0}}, Page(Links(), 'catalogue/a/'))
        self.assertIn('<td data-climate="4A">2.0</td>', html)
        self.assertIn('class="ea-climates"', html)

    def test_zones_of_labels_and_keys(self):
        self.assertEqual(zone('1A-tropical-semi-conditioned'), '1A')
        self.assertEqual(zone('3-a.atlanta'), '3A')
        self.assertEqual(zone('8'), '8')
        self.assertIsNone(zone('Atlanta'))

    def test_annual_series_summarise_by_month_and_hour(self):
        values = [float(h % 24) for h in range(8760)]
        months, hours = annual_summary(values)
        self.assertEqual(len(months), 12)
        self.assertEqual(hours, [float(h) for h in range(24)])
        self.assertTrue(all(abs(m-11.5) < 1e-9 for m in months))
        values[0] = None
        self.assertEqual(annual_summary(values)[1][0], 0.0)

    def test_annual_schedule_has_plots_and_no_hourly_table(self):
        record = {'id': 's-annual-1', 'units': '1', 'annual_values': [0.5]*8760, 'calendar': {'seed': 1}}
        html = schedule(record, Page(links(**{'s-annual-1': 'catalogue/a/'}), 'catalogue/a/'))
        self.assertEqual(html.count('<svg'), 2)
        self.assertIn('8,760 hourly values', html)
        self.assertLess(html.count('<td>'), 40)

    def test_rule_schedules_list_rules_and_profiles(self):
        record = {'id': 's-rules-1', 'units': 'W', 'rules': [{'day': 'd-1', 'day_types': 'Mon', 'start_date': '2006-01-01'},
                                                             {'day': 'd-2', 'day_types': 'Sun'}, {'day': 'd-1', 'day_types': 'Hol'}],
                  'days': {'d-1': [1.0]*24, 'd-2': [None]*12+[0.0]*12}}
        html = schedule(record, Page(Links(), 'catalogue/a/'))
        self.assertIn('P1', html)
        self.assertIn('P2', html)
        self.assertEqual(html.count('<svg'), 2)
        self.assertIn('id="s-rules-1"', html)

    def test_plot_leaves_gaps_for_nulls(self):
        self.assertEqual(plot([1.0, None, 2.0], ['', '', '']).count('<polyline'), 2)
        self.assertIn('No known values', plot([None, None], ['', '']))


class PageTests(unittest.TestCase):
    def test_shared_fields_split_one_level_down(self):
        documents = [{'source': {'evidence': [1], 'climate': '1A'}, 'kind': 'set', 'components': {'Wall': 1, 'Roof': 2}, 'only': 1},
                     {'source': {'evidence': [1], 'climate': '2A'}, 'kind': 'set', 'components': {'Wall': 1, 'Roof': 3}}]
        shared, own = split_shared(documents)
        self.assertEqual(shared, {'source': {'evidence': [1]}, 'kind': 'set', 'components': {'Wall': 1}})
        self.assertEqual(own[0], {'source': {'climate': '1A'}, 'components': {'Roof': 2}, 'only': 1})
        self.assertEqual(own[1], {'source': {'climate': '2A'}, 'components': {'Roof': 3}})

    def test_context_axes(self):
        self.assertEqual(context_facets('4-a', {}), {'climate': '4A', 'zone': '4A'})
        self.assertEqual(context_facets('0-a.90-1-2007-large-office', {}),
                         {'climate': '0A', 'zone': '0A', 'reference': '90-1-2007-large-office'})
        self.assertEqual(context_facets('1-a-tropical.slab', {'climate': '1A-tropical', 'climate_zone': '1A', 'foundation': 'slab'}),
                         {'climate': '1A-tropical', 'zone': '1A', 'foundation': 'slab'})
        self.assertEqual(context_facets('3-a.atlanta', {'climate': '3A', 'location': 'Atlanta'}),
                         {'climate': '3A', 'zone': '3A', 'location': 'Atlanta'})

    def test_pages_are_one_raw_html_block(self):
        text = markdown('A "title"', '<p>a</p>\n\n<p>b</p>')
        front, body = text.split('---\n\n', 1)
        self.assertIn('title: "A \\"title\\""', front)
        self.assertNotIn('\n\n', body.strip())
        self.assertTrue(body.startswith('<div class="ea-suite" markdown="0" data-search-exclude>'))


class ReleaseTests(unittest.TestCase):
    def test_the_newest_release_is_chosen_by_number(self):
        with tempfile.TemporaryDirectory() as temporary:
            for name in ('v1.9.0', 'v1.10.0', 'v1.2.0', 'notes'):
                (Path(temporary)/name).mkdir()
            with patch.object(site_release, 'RELEASES', Path(temporary)):
                self.assertEqual(site_release.releases(), ['1.2.0', '1.9.0', '1.10.0'])
                self.assertEqual(site_release.newest(), '1.10.0')

    def test_page_slugs_drop_the_folder_and_the_content_hash(self):
        self.assertEqual(site_release.page_slug('90-1-2019.office.source.break-room.589d96', 'commercial/90-1-2019/office/'), 'source/break-room')
        self.assertEqual(site_release.page_slug('iecc-2021.single-family.envelope.2f6679', 'residential/iecc-2021/single-family/'), 'envelope')
        self.assertEqual(site_release.folder_of('commercial/90-1-2019/office/programs/source/x.json'), 'commercial/90-1-2019/office/')
        self.assertIsNone(site_release.folder_of('commercial/90-1-2019/library/assemblies.json'))
        self.assertIsNone(site_release.folder_of('evidence/glossary.json'))


class LayoutTests(unittest.TestCase):
    def test_template_libraries_never_take_a_building_type_folder_url(self):
        from scripts.suite_site import Site, library_url
        self.assertNotEqual(library_url('commercial/90-1-2019/'), Site.folder_url(None, 'commercial/90-1-2019/library/'))

    def test_two_pages_never_share_a_path(self):
        from scripts.suite_site import Site
        with tempfile.TemporaryDirectory() as temporary:
            site = Site.__new__(Site)
            site.target, site.written = Path(temporary), set()
            site.write('catalogue/a/index.md', 'one')
            with self.assertRaises(ValueError):
                site.write('catalogue/a/index.md', 'two')


class CheckTests(unittest.TestCase):
    def site(self, temporary):
        root = Path(temporary)
        store = site_store.Store(root)
        descriptor = store.put({'id': 'p.a', 'version': 'source'})
        page = root/'catalogue/p/index.html'
        page.parent.mkdir(parents=True)
        page.write_text(f'<a href="../../">home</a><a href="#x">x</a><span id="x" class="ea-json" '
                        f'data-json=\'{json.dumps({**descriptor, "href": "../../"+descriptor["href"]})}\'></span>', encoding='utf-8')
        (root/'index.html').write_text('<a href="catalogue/p/#x">p</a>', encoding='utf-8')
        manifest = {'release': '9.9.9', 'partial': False, 'construction_sets': {},
                    'programs': {'p.a': {'page': 'catalogue/p/', 'source': descriptor['href'], 'filled': None, 'filled_reason': 'source only'}}}
        return root, descriptor, manifest

    def test_a_consistent_site_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, _, manifest = self.site(temporary)
            pages = site_check.parse(root)
            self.assertEqual(site_check.check_links(root, pages), [])
            self.assertEqual(site_check.check_store(root, pages), [])
            self.assertEqual(site_check.check_coverage(root, manifest, ({'p.a'}, {})), [])

    def test_broken_links_store_files_and_coverage_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, descriptor, manifest = self.site(temporary)
            (root/'index.html').write_text('<a href="catalogue/p/#missing">p</a><a href="catalogue/none/">n</a>', encoding='utf-8')
            (root/descriptor['href']).write_bytes(b'changed')
            pages = site_check.parse(root)
            self.assertEqual(len(site_check.check_links(root, pages)), 2)
            self.assertEqual(len(site_check.check_store(root, pages)), 2)
            self.assertEqual(site_check.check_coverage(root, manifest, ({'p.a', 'p.b'}, {})), ['No page for p.b'])
            (root/'definitions').mkdir()
            self.assertEqual(site_check.check_retired(root), ['Retired route present: definitions/'])

    def test_a_sample_excuses_links_into_unbuilt_folders_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, _, manifest = self.site(temporary)
            (root/'index.html').write_text('<a href="catalogue/commercial/90-1-2019/office/programs/source/x/">out</a>'
                                           '<a href="catalogue/p/#missing">p</a><a href="catalogue/commercial/90-1-2019/template-library/">lib</a>',
                                           encoding='utf-8')
            pages = site_check.parse(root)
            sample = {**manifest, 'partial': True, 'sample': {'folders_per_template': 1, 'folders': ['commercial/90-1-2019/retail-standalone/']}}
            errors = site_check.check_links(root, pages, unbuilt=site_check.unbuilt_folder(sample))
            self.assertEqual(len(errors), 2)  # the fragment and the library page; the office folder was not built
            self.assertEqual(len(site_check.check_links(root, pages, unbuilt=site_check.unbuilt_folder(manifest))), 3)

    def test_the_ceiling_is_one_gigabyte(self):
        self.assertEqual(site_check.CEILING, 1_000_000_000)


if __name__ == '__main__':
    unittest.main()
