"""Source-backed component geometry declarations shared by export and validation."""
import copy


def geometry_rule(a):
    """Move genuine geometry conventions into the component rule without evaluating a BEM."""
    app=a['applicability']
    rule={'area':{'method':'bem_surface_area','unit':'m2'},
          'layers':{'orientation':a['layer_orientation'],'paired_surface_policy':'reverse_order',
                    'source_reference_reversed':app.get('reverse_for_adjacent_surface',False)}}
    if a['role']=='InteriorPartition' and 'area_per_conditioned_floor_area' in app:
        rule['area']={'method':'source_partition_cfa_scaling','unit':'m2',
            'area_per_conditioned_floor_area':app['area_per_conditioned_floor_area'],
            'area_convention':app['area_convention']}
    if a['role']=='OrdinaryInteriorFloor':
        rule['area']={'method':'source_ordinary_interstory_scaling','unit':'m2',
            'source_area_rule':app['consumer_area_rule'],'paired_floor_and_ceiling':True,
            'source_activation_threshold_m2':0.09290304}
    if 'source_roof_pitch_rad' in app:
        rule['roof']={'source_pitch_rad':app['source_roof_pitch_rad'],'unit':'rad',
            'applicability':'source_pitch_only','different_pitch_policy':'source_recipe_reevaluation_required',
            'source_film_rule':app['source_film_rule']}
    if 'overhang_geometry' in a.get('solar_modifiers',{}):
        rule['overhang']=copy.deepcopy(a['solar_modifiers']['overhang_geometry'])
    return rule
