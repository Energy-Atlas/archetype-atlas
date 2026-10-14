"""Mixtures conserve individually generated loads with explicit physical bases."""
import copy
import importlib.util
import math
import unittest
from unittest.mock import patch
from tests.test_schedule_generator_pilot import GeneratorCase, OFFICE, OCCUPIED, VACANT, PLENUM
from atlas_schedules.errors import GeneratorError
from atlas_schedules.comparison import compare_bundles


class MixtureTests(GeneratorCase):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(importlib.util.find_spec('atlas_schedules.mixtures'))
        from atlas_schedules import compose_constituents
        self.compose = compose_constituents

    def mixture(self, instances, explicit=False):
        result = {'program_id':'experiment-mix','composition_id':None,
                  'members':[{'instance_key':i['key'],'weight':1/len(instances)} for i in instances]}
        if explicit:
            result.update(result_basis='floor_area', denominator={'value':100,'unit':'m2','evidence':{'caller':'declared experiment area'}})
        return result

    def extent(self, basis, value, unit):
        return {'extents':{basis:{'value':value,'unit':unit,'evidence':{'caller':'explicit experiment extent'}}}}

    def test_mixed_families_and_29_members(self):
        instances = [self.instance('apt',OCCUPIED,basis=self.extent('dwelling_unit',1,'dwelling'))]
        instances += [self.instance('office-'+str(i),OFFICE,group='building',
                         basis=self.extent('floor_area',100,'m2')) for i in range(28)]
        mixture = self.mixture(instances,True)
        bundle = self.generate(self.params(instances,mixture),42)
        self.assert_conserved(bundle)
        self.assertEqual(len(bundle['constituents']),30)
        mixed = bundle['constituents'][-1]
        for binding in [bundle['bindings'][i] for i in mixed['binding_indices'] if bundle['bindings'][i]['kind']=='load']:
            evidence = binding['reference_target']['evidence']
            components = evidence['components']
            trajectory = bundle['schedules'][binding['schedule_id']]['values']
            amplitude = binding['effective_magnitude']['value']
            for hour in range(8760):
                expected = math.fsum(c['factor'] * bundle['bindings'][c['binding_index']]['effective_magnitude']['value'] *
                                     bundle['schedules'][c['schedule_id']]['values'][hour] for c in components)
                self.assertTrue(math.isclose(trajectory[hour]*amplitude,expected,rel_tol=1e-12,abs_tol=1e-12))
            target = math.fsum(c['factor']*bundle['bindings'][c['binding_index']]['reference_target']['total'] for c in components)
            self.assertTrue(math.isclose(binding['reference_target']['total'],target,rel_tol=1e-12))
        pairs = mixed['generation']['people_pairs']
        heat = bundle['schedules'][mixed['schedule_ids']['people_heat']]['values']
        self.assertEqual(len(pairs),29)
        for hour in range(8760):
            expected = math.fsum(p['density']*p['factor']*bundle['schedules'][p['occupancy_schedule_id']]['values'][hour]*
                                 bundle['schedules'][p['activity_schedule_id']]['values'][hour] for p in pairs)
            self.assertAlmostEqual(heat[hour],expected,places=12)

    def test_group_conflict_and_shared_service_identity(self):
        instances = [self.instance('a',group='shared'),self.instance('b',group='shared')]
        bundles = [self.generate(self.params([i]),42) for i in instances]
        # Same source descriptor is two physical demands unless explicitly shared.
        for b in bundles:
            c=b['constituents'][0]
            demand=next(d for d in c['demands'] if d['quantity']=='hot_water_volume')
            c['shared_services']=[{'source_service_id':'same-source','demand_id':demand['demand_id']}]
        plain=self.compose(bundles,self.mixture(instances),bundles[0]['metadata']['calendar'])
        water=next(b for b in plain['bindings'] if b['instance_key']==plain['constituents'][-1]['instance_key']
                   and b['reference_target']['quantity']=='hot_water_volume')
        self.assertEqual(len(water['reference_target']['evidence']['components']),2)
        for b in bundles:
            b['constituents'][0]['basis_bindings']=self.extent('floor_area',100,'m2')
            b['constituents'][0]['shared_services'][0].update(physical_id='one-tank',mode='whole',
                extent={'value':100,'unit':'m2','evidence':{'fixture':'explicit 100 square metre source service extent'}},
                allocation={'informational_program_share':0.5})
        shared=self.compose(bundles,self.mixture(instances,True),bundles[0]['metadata']['calendar'])
        self.assertEqual(len(shared['constituents'][-1]['shared_services']),1)
        self.assertEqual(shared['constituents'][-1]['shared_services'][0]['physical_id'],'one-tank')
        shared_water=next(b for b in shared['bindings'] if b['instance_key']==shared['constituents'][-1]['instance_key']
                         and b['kind']=='load' and b['reference_target']['quantity']=='hot_water_volume')
        self.assertEqual(shared_water['reference_target']['total'],water['reference_target']['total'])
        conflict=copy.deepcopy(bundles)
        conflict[1]['constituents'][0]['shared_services'][0]['mode']='allocated'
        with self.assertRaises(GeneratorError):self.compose(conflict,self.mixture(instances,True),bundles[0]['metadata']['calendar'])
        conflict=copy.deepcopy(bundles)
        conflict[1]['constituents'][0]['shared_services'][0]['extent']['value']=2
        with self.assertRaises(GeneratorError):self.compose(conflict,self.mixture(instances,True),bundles[0]['metadata']['calendar'])
        # Real resolution, changed controlled context at the producer boundary.
        from atlas_schedules.programs import resolve_program
        def conflict(program, inputs, resources):
            result=resolve_program(program,inputs,resources)
            if program==PLENUM: result['inputs']['source_context']['occupancy_adjustment']['peak_occ_frac']=0.5
            return result
        with patch('atlas_schedules.generator.resolve_program',side_effect=conflict):
            with self.assertRaises(GeneratorError) as raised:
                self.generate(self.params([self.instance('office',group='shared'), self.instance('plenum',PLENUM,'shared')]),42)
        self.assertEqual(raised.exception.code,'operating_group_conflict')

    def test_singleton_zero_group_and_incompatible_scale(self):
        instances=[self.instance('one',VACANT)]
        original=self.generate(self.params(instances),42)
        mixed=self.compose([original],self.mixture(instances),original['metadata']['calendar'])
        source=original['bindings'][0]; result=mixed['bindings'][len(original['bindings'])]
        self.assertEqual(result['reference_target']['total'],source['reference_target']['total'])
        self.assertEqual(mixed['schedules'][result['schedule_id']]['values'],original['schedules'][source['schedule_id']]['values'])
        inactive=[self.instance('empty',PLENUM)]
        zero=self.generate(self.params(inactive,self.mixture(inactive)),0)
        self.assertEqual(zero['schedules'],{})
        bad=[self.instance('a',OCCUPIED),self.instance('b',OFFICE)]
        with self.assertRaises(GeneratorError) as raised: self.generate(self.params(bad,self.mixture(bad)),42)
        self.assertEqual(raised.exception.code,'incompatible_scale')
        bad[0]['basis_bindings']=self.extent('dwelling_unit',1,'m2')
        bad[1]['basis_bindings']=self.extent('floor_area',100,'m2')
        with self.assertRaises(GeneratorError): self.generate(self.params(bad,self.mixture(bad,True)),42)
        invalid=copy.deepcopy(self.mixture(instances));invalid['composition_id']='unknown'
        with self.assertRaises(GeneratorError): self.generate(self.params(instances,invalid),42)

    def test_comparison_distinguishes_continuous_receipts_rng_and_versions(self):
        b=self.generate(self.params([self.instance('office')]),42)
        policy=self.resources.get('reference','comparison-policy')
        other=copy.deepcopy(b)
        context=other['constituents'][0]['generation']['source_context']
        context['operating_receipt']['rng']['python_version']='other-runtime'
        context['transforms']['lighting']['daily_profiles'][0][0][1]+=1e-10
        self.assertEqual(compare_bundles(other,b,policy),[])
        context['operating_receipt']['draw_receipts'][0]['uniform']+=1e-10
        self.assertTrue(compare_bundles(other,b,policy))
        for change in ('source_evidence','option','source_rule'):
            changed=copy.deepcopy(b)
            if change=='source_evidence':changed['constituents'][0]['demands'][0]['evidence']['original_value']+=1e-10
            elif change=='option':changed['constituents'][0]['generation']['source_context']['operating_receipt']['selected_options']['weekday_start_time']='different-source-choice'
            else:changed['constituents'][0]['generation']['source_context']['slot_sources']['lighting']['rules'][0]['values'][0]+=1e-10
            self.assertTrue(compare_bundles(changed,b,policy),change)
        other=copy.deepcopy(b)
        other['constituents'][0]['generation']['source_context']['transforms']['lighting']['daily_profiles'][0][0][1]+=0.01
        self.assertTrue(compare_bundles(other,b,policy))

    def test_explicit_multiplicity_active_controls_and_annual_heat_fractions(self):
        instances=[self.instance('a',OCCUPIED),self.instance('b',VACANT,basis={'multiplicity':0})]
        bundle=self.generate(self.params(instances,self.mixture(instances)),42)
        mixed=bundle['constituents'][-1]
        control=next(c for c in mixed['controls'] if c['slot']=='heating_setpoint')
        self.assertEqual(control['evidence']['active_members'],['a'])
        # Distinct source budgets/fractions for the same refrigerator demand.
        for demand in mixed['demands']:
            if demand['heat_fractions'] is None: continue
            components=demand['evidence']['components']
            energies=[c['factor']*bundle['bindings'][c['binding_index']]['reference_target']['total'] for c in components]
            for name,value in demand['heat_fractions'].items():
                wanted=math.fsum(e*c['heat_fractions'][name] for c,e in zip(components,energies) if e>0)/math.fsum(energies)
                self.assertAlmostEqual(value,wanted,places=12)
        repeated=[self.instance('v',VACANT,basis={'multiplicity':3})]
        repeated_bundle=self.generate(self.params(repeated,self.mixture(repeated)),42)
        binding=next(b for b in repeated_bundle['bindings'] if b['instance_key']==repeated_bundle['constituents'][-1]['instance_key'] and b['kind']=='load')
        self.assertAlmostEqual(binding['reference_target']['total'],3*455700,places=7)

    def test_mixed_reference_aliases_compare_by_scientific_ownership(self):
        from tests.test_schedule_generator_pilot import OFFICE
        instances=[self.instance('one',OFFICE)]
        b=self.generate(self.params(instances,self.mixture(instances)),42)
        other=copy.deepcopy(b)
        mapping={sid:'opaque-'+str(i) for i,sid in enumerate(other['schedules'])}
        other['schedules']={mapping[sid]:dict(s,id=mapping[sid]) for sid,s in other['schedules'].items()}
        def aliases(value):
            if isinstance(value,dict):
                return {k:aliases(v) for k,v in value.items()}
            if isinstance(value,list):return [aliases(v) for v in value]
            return mapping.get(value,value) if isinstance(value,str) else value
        other['constituents']=aliases(other['constituents'])
        other['bindings']=aliases(other['bindings'])
        self.assertEqual(compare_bundles(other,b,self.resources.get('reference','comparison-policy')),[])

    def test_precomputed_realizations_keep_truthful_seed_and_group_receipts(self):
        instances=[self.instance('a',VACANT),self.instance('b',VACANT)]
        incoming=[self.generate(self.params([i]),42) for i in instances]
        result=self.compose(incoming,self.mixture(instances),incoming[0]['metadata']['calendar'])
        self.assertEqual(result['generation']['method'],'precomputed_bundle_composition_v1')
        self.assertNotIn('unit_seeds',result['generation'])
        self.assertEqual([r['unit_seeds'] for r in result['generation']['input_generation_receipts']],
                         [{'a':42},{'b':42}])
        coordinated=[self.instance('office-a',group='building'),self.instance('office-b',group='building')]
        conflict=[self.generate(self.params([coordinated[0]]),42), self.generate(self.params([coordinated[1]]),51)]
        with self.assertRaises(GeneratorError) as raised:
            self.compose(conflict,self.mixture(coordinated),conflict[0]['metadata']['calendar'])
        self.assertEqual(raised.exception.code,'operating_group_conflict')

    def test_fraction_normalization_uses_sum_of_bound_magnitudes(self):
        instances=[self.instance('a',group='first'),self.instance('b',group='second')]
        bundle=self.generate(self.params(instances,self.mixture(instances)),42)
        mixed=bundle['constituents'][-1]
        for index in mixed['binding_indices']:
            binding=bundle['bindings'][index]
            if binding['kind']!='load':continue
            components=binding['reference_target']['evidence']['components']
            expected=math.fsum(c['factor']*bundle['bindings'][c['binding_index']]['effective_magnitude']['value'] for c in components)
            self.assertTrue(math.isclose(binding['effective_magnitude']['value'],expected,rel_tol=1e-12))

    def test_explicit_per_person_water_scaling_preserves_volume(self):
        instances=[self.instance('office',basis=self.extent('floor_area',100,'m2'))]
        mixture=self.mixture(instances,True)
        mixture.update(result_basis='person',denominator={'value':10,'unit':'person','evidence':{'caller':'Explicit normalization count'}})
        bundle=self.generate(self.params(instances,mixture),42)
        self.assert_conserved(bundle)
        water=next(b for b in bundle['bindings'] if b['kind']=='load' and b['instance_key']==bundle['constituents'][-1]['instance_key']
                   and b['reference_target']['quantity']=='hot_water_volume')
        source=next(b for b in bundle['bindings'] if b['kind']=='load' and b['instance_key']=='office' and b['reference_target']['quantity']=='hot_water_volume')
        self.assertEqual(water['reference_target']['unit'],'m3/person')
        self.assertEqual(water['effective_magnitude']['unit'],'m3/s/person')
        self.assertAlmostEqual(water['reference_target']['total'],10*source['reference_target']['total'],places=12)
        mixture['denominator']['value']=1e9  # controlled tolerance boundary, not a population realization
        tiny=self.generate(self.params(instances,mixture),42)
        changed=copy.deepcopy(tiny)
        demand=next(d for d in changed['constituents'][-1]['demands'] if d['quantity']=='hot_water_volume')
        demand['annual_target']['total']+=1e-9
        self.assertTrue(compare_bundles(changed,tiny,self.resources.get('reference','comparison-policy')))

    def test_explicit_legacy_area_alias_has_provenance_and_conflict_guard(self):
        instances=[self.instance('office',basis={'floor_area_m2':100})]
        bundle=self.generate(self.params(instances,self.mixture(instances,True)),42)
        self.assert_conserved(bundle)
        area=bundle['constituents'][0]['basis_bindings']['extents']['floor_area']
        self.assertEqual(area['value'],100)
        self.assertEqual(area['unit'],'m2')
        receipt=bundle['constituents'][0]['generation']['basis_alias_receipts']['floor_area_m2']
        self.assertEqual(receipt['original_value'],100)
        self.assertEqual(receipt['original_unit'],'m2')
        self.assertIn('/basis_bindings/floor_area_m2',receipt['source_locator'])
        instances[0]['basis_bindings'].update(self.extent('floor_area',200,'m2'))
        with self.assertRaises(GeneratorError) as raised:self.generate(self.params(instances),42)
        self.assertEqual(raised.exception.code,'incompatible_scale')
        for value in (True,-1,float('nan')):
            instances[0]['basis_bindings']={'floor_area_m2':value}
            with self.assertRaises(GeneratorError):self.generate(self.params(instances),42)
