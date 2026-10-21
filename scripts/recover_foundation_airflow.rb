# frozen_string_literal: true
# Recover source host airflow coefficients with explicit SI unit probes.
require 'json'
source,input,output,register_helper,post_hpxml,harness=ARGV
require File.join(File.expand_path(source),'measures/ResStockArguments/measure')

def atlas_host_airflow(b,r,model)
  Geometry.apply_foundation_and_walls_top(b)
  Airflow.set_wind_speed_correction(model,b)
  ap=b.site.additional_properties
  ref=UnitConversions.convert(ap.height,'ft','m')
  grade=UnitConversions.convert(b.building_construction.additional_properties.foundation_height_above_grade,'ft','m')
  probes=[1.0,2.5,5.0].map do |height|
    cw,cs=Airflow.calc_wind_stack_coeffs(b,0.4,0.5,HPXML::LocationGarage,UnitConversions.convert(height,'m','ft'))
    {height_m:height,foundation_top_m:grade,wind_coefficient:cw,
     stack_coefficient_m2_s2_K:UnitConversions.convert(cs,'ft^2/(s^2*R)','L^2/(s^2*cm^4*K)')*100.0}
  end
  ela_factor=Airflow.get_infiltration_SLA_from_ACH50(1.0,UnitConversions.convert(1.0,'m','ft'))*3600.0
  {record_id:r.fetch('record_id'),source_site_type:b.site.site_type,
   source_shielding:b.site.shielding_of_home,engine_site_terrain:model.getSite.terrain,
   ela_volume_coefficient_s_m:ela_factor,
   stack_height_coefficient_m_s2_K:probes[0][:stack_coefficient_m2_s2_K],
   wind_reference_height_m:ref,wind_height_exponent:2*ap.site_terrain_exponent,
   wind_coefficient_scale:probes[0][:wind_coefficient]/((1.0+grade)/ref)**(2*ap.site_terrain_exponent),
   probes:probes,
   vented_crawlspace:{reference_height_m:UnitConversions.convert(Airflow::ReferenceHeight,'ft','m'),
       height_exponent:0.4,normalized_leakage_multiplier:1000.0},
   unvented_ach_per_s:Airflow::UnventedSpaceACH/3600.0,
   original_source_constants:{pressure_exponent:Airflow::InfilPressureExponent,hor_leak_fraction:0.4,neutral_level:0.5,
       gravity_ft_s2:Airflow::Gravity,assumed_indoor_temperature_F:Airflow::AssumedInsideTemp,
       reference_height_ft:Airflow::ReferenceHeight,unvented_ach:Airflow::UnventedSpaceACH}}
end

code=File.read(harness)
start=code.index('  total, exterior = Defaults.get_compartmentalization_boundary_areas(b)')
finish=code.index("\nend\nFile.write(output",start)
raise 'Unrecognized pinned geometry/default harness' if start.nil? || finish.nil?
code[start...finish]='  atlas_host_airflow(b,r,model)'
eval(code,binding,harness)
