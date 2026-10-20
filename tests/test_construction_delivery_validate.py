"""All-context consumer checks do not regenerate platform-dependent fit IDs."""
import copy
import unittest
from scripts.construction_distribution import load_current_release
from scripts.construction_mass_release import load_release,unified_index,PILOTS
from scripts.construction_weighting import load_profiles
from scripts.construction_mass_accounting import BatchMassValidationCache


class ConstructionDeliveryValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=load_current_release();cls.mass=load_release()
        cls.index=unified_index();cls.profiles=load_profiles()
        cls.cid=PILOTS['medium-office-2019-3B']

    def check(self,index=None,source=None):
        from scripts.construction_delivery_validate import validate_context
        return validate_context(self.cid,source or self.source,self.mass,index or self.index,
                                self.profiles,BatchMassValidationCache())

    def test_frozen_pilot_validates_both_consumer_documents(self):
        self.assertEqual(self.check(),('2.1.0','1.2.0'))

    def test_envelope_capacity_corruption_is_rejected(self):
        header=self.index['catalogue']['contexts'][self.cid]
        body=self.index['components'][header['component_set_id']]
        aid=body['components']['ExteriorWall']['assembly_id']
        index={**self.index,'assemblies':dict(self.index['assemblies'])}
        index['assemblies'][aid]=copy.deepcopy(index['assemblies'][aid])
        index['assemblies'][aid]['layers'][0]['C']*=2
        with self.assertRaisesRegex(ValueError,'capacity'):
            self.check(index=index)

    def test_changed_source_infiltration_is_rejected(self):
        source={**self.source,'contexts':dict(self.source['contexts'])}
        source['contexts'][self.cid]=copy.deepcopy(source['contexts'][self.cid])
        source['contexts'][self.cid]['infiltration']['natural_ach']['value']*=2
        with self.assertRaisesRegex(ValueError,'infiltration'):
            self.check(source=source)

    def test_missing_frozen_material_is_rejected(self):
        header=self.index['catalogue']['contexts'][self.cid]
        body=self.index['components'][header['component_set_id']]
        aid=body['components']['ExteriorWall']['assembly_id']
        index={**self.index,'assemblies':dict(self.index['assemblies'])}
        del index['assemblies'][aid]
        with self.assertRaises((ValueError,KeyError)):
            self.check(index=index)


if __name__=='__main__':unittest.main()
