import tempfile
from pathlib import Path
import unittest
from scripts.definition_contract import DefinitionBundle,record
from scripts.definition_site import generate


class DefinitionSiteTests(unittest.TestCase):
    def test_two_gates_three_kinds_and_context_facets(self):
        bundle=DefinitionBundle()
        source={'id':'p','building_type':'MediumOffice','template':'90.1-2019','source_family':'code_prototype_rules'}
        p=record('program',source,'Office');p.update(detail='SourcePrograms',available_details=['SourcePrograms'],loads=[])
        bundle['programs']=[p]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);generate(bundle,root,publish=False)
            gate=(root/'catalogue.md').read_text(encoding='utf-8')
            self.assertEqual(gate.count('class="definition-gate"'),2)
            self.assertIn('Residential',gate);self.assertIn('Non Residential',gate)
            for branch in ('residential','nonresidential'):
                page=(root/f'catalogue/{branch}/index.md').read_text(encoding='utf-8')
                self.assertEqual(page.count('class="definition-kind"'),3)
            programs=(root/'catalogue/nonresidential/program/index.md').read_text(encoding='utf-8')
            self.assertIn('Program detail',programs)
            self.assertNotIn('data-filter="climate"',programs)
            self.assertIn('Office',programs)
            self.assertTrue((root/f'definitions/{p["id"]}.md').exists())


if __name__=='__main__':unittest.main()
