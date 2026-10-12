import copy
import unittest

from scripts.common import ROOT,load_json
from scripts.recover_energy_inputs import CONSTRUCTION,SYSTEM,BASE
from scripts.definition_release import read_bundle
from scripts.energy_recovery_validation import validate, pilot_exports


class RecoveryValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=load_json(CONSTRUCTION)
        cls.s=load_json(SYSTEM)
        cls.bundle=read_bundle(BASE)

    def test_full_recovery_inventory_has_no_orphans(self):
        receipt=validate(self.c,self.s,self.bundle,check_inputs=False)
        self.assertEqual(receipt['construction_records'],3798)
        self.assertEqual(receipt['hvac_records'],1046)
        self.assertEqual(receipt['recovered_glazing_assemblies'],12)
        self.assertEqual(receipt['material_default_instances'],166)

    def test_unknown_active_inputs_cannot_be_marked_ready(self):
        s=copy.deepcopy(self.s)
        row=next(iter(s['records'].values()))
        row['readiness']='resolved'
        with self.assertRaisesRegex(ValueError,'readiness'):
            validate(self.c,s,self.bundle,check_inputs=False)

    def test_negative_heater_loss_is_rejected(self):
        s=copy.deepcopy(self.s)
        row=next(r for r in s['water_heaters'].values() if 'tank_loss_coefficient' in r['fields'])
        row['fields']['tank_loss_coefficient']['value']=-1
        with self.assertRaisesRegex(ValueError,'physical'):
            validate(self.c,s,self.bundle,check_inputs=False)

    def test_recovered_layers_reject_invalid_physics(self):
        cases=[('SimpleGlazing','u_W_m2_K',-4),('SimpleGlazing','shgc',1.1),
               ('StandardOpaqueMaterial','thickness_m',0),
               ('StandardOpaqueMaterial','conductivity_W_m_K',float('inf')),
               ('MasslessOpaqueMaterial','resistance_m2_K_W',True)]
        for model,field,value in cases:
            with self.subTest(model=model,field=field):
                c=copy.deepcopy(self.c)
                layer=next(l for r in c['records'].values() for l in r['recovered'].get('layers',[])
                           if l['properties']['model']==model)
                layer['properties'][field]=value
                with self.assertRaisesRegex(ValueError,'physical'):
                    validate(c,self.s,self.bundle,check_inputs=False)

    def test_secondary_heaters_retain_their_producing_source_method(self):
        components=[i for r in self.s['records'].values() for i in r['recovered'].get('equipment',[])
                    if i['role']=='heating' and i['native_source_fields']['id']=='HeatingSystem2']
        self.assertEqual(len(components),6)
        for component in components:
            for field in component['fields'].values():
                self.assertIn('BuildResidentialHPXML.set_secondary_heating_systems',
                              field['evidence']['source_locator'])

    def test_invalid_provenance_is_rejected(self):
        c=copy.deepcopy(self.c)
        row=next(iter(c['materials'].values()))
        next(iter(row['fields'].values()))['evidence']['source_file_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'provenance'):
            validate(c,self.s,self.bundle,check_inputs=False)

    def test_orphan_material_default_is_rejected(self):
        c=copy.deepcopy(self.c)
        row=next(iter(c['materials'].values()))
        row['id']='not-a-source-material'
        c['materials']['not-a-source-material']=row
        with self.assertRaisesRegex(ValueError,'material'):
            validate(c,self.s,self.bundle,check_inputs=False)

    def test_pilots_keep_contracts_independent(self):
        pilots=pilot_exports(self.c,self.s,self.bundle)
        self.assertEqual(pilots['medium-office-construction']['kind'],'construction')
        self.assertEqual(pilots['medium-office-system']['kind'],'system')
        self.assertEqual(pilots['residential-construction']['kind'],'construction')
        self.assertEqual(pilots['residential-system']['kind'],'system')
        self.assertTrue(pilots['medium-office-system']['unresolved'])
        self.assertNotIn('programs',pilots['medium-office-system'])
        self.assertNotIn('programs',pilots['medium-office-construction'])


if __name__=='__main__':
    unittest.main()
