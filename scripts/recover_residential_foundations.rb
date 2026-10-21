# frozen_string_literal: true
# Pinned foundation defaults, layers and Kiva only; no HVAC or simulation.
require 'json'
source,input,output,register_helper,post_hpxml,harness,assembly_harness=ARGV
require File.join(File.expand_path(source),'measures/ResStockArguments/measure')
require File.join(File.expand_path(source),'resources/hpxml-measures/HPXMLtoOpenStudio/measure')

# Reuse the frozen capture helpers without executing their above-ground entrypoint.
helpers=File.read(assembly_harness)
eval(helpers[helpers.index('def source_material')...helpers.index('def atlas_enclosure')],binding,assembly_harness)

def atlas_fields(object)
  result={}
  (0...object.numFields).each do |i|
    field=object.iddObject.getField(i)
    key=field.is_initialized ? field.get.name : "field_#{i}"
    next if ['Handle','Name'].include?(key)
    key="#{key}__#{i}" if result.key?(key)
    v=object.getString(i,true)
    value=v.is_initialized ? v.get : nil
    if !value.nil? && value.match?(/\A[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?\z/)
      number=object.getDouble(i,true)
      value=number.get if number.is_initialized
    end
    result[key]=value
  end
  result
end

# Capture the source initialization rule inputs without choosing weather, a run
# calendar or a program thermostat. The consumer must evaluate this source rule.
module AtlasGroundInitialization
  def apply_kiva_initial_temperature(foundation,weather,b,header,spaces,schedules,host)
    walls=b.foundation_walls.select { |w| w.interior_adjacent_to==host && w.exterior_adjacent_to==HPXML::LocationGround }
    wall_ins=walls.any? { |w| w.insulation_assembly_r_value.to_f>5 || w.insulation_exterior_r_value.to_f+w.insulation_interior_r_value.to_f>0 }
    ceiling_ins=b.floors.any? { |f| f.interior_adjacent_to==HPXML::LocationConditionedSpace && f.exterior_adjacent_to==host && f.insulation_assembly_r_value>5 }
    spec={host:host,walls_insulated:wall_ins,ceiling_insulated:ceiling_ins,
      source_method:'Constructions.apply_kiva_initial_temperature',
      disposition:'requires_consumer_weather_calendar_and_conditioned_setpoints'}
    # Numerical verification uses declared test inputs only, never catalogue defaults.
    probes=[]
    [true,false].each do |controls|
      [-5.0,12.5,30.0].each do |outdoor_c|
        test_model=OpenStudio::Model::Model.new
        test_space=OpenStudio::Model::Space.new(test_model)
        zone=OpenStudio::Model::ThermalZone.new(test_model)
        test_space.setThermalZone(zone)
        if controls
          thermostat=OpenStudio::Model::ThermostatSetpointDualSetpoint.new(test_model)
          [[:setHeatingSetpointTemperatureSchedule,20.0],[:setCoolingSetpointTemperatureSchedule,26.0]].each do |setter,temp|
            schedule=OpenStudio::Model::ScheduleRuleset.new(test_model)
            schedule.defaultDaySchedule.addValue(OpenStudio::Time.new(0,24,0,0),temp)
            thermostat.send(setter,schedule)
          end
          zone.setThermostatSetpointDualSetpoint(thermostat)
        end
        weather_data=Struct.new(:MonthlyAvgDrybulbs,:ShallowGroundMonthlyTemps).new(
          Array.new(12,UnitConversions.convert(outdoor_c,'C','F')),Array.new(12,50.0))
        test_weather=Struct.new(:data).new(weather_data)
        test_header=Struct.new(:sim_begin_month,:sim_begin_day,:sim_calendar_year).new(1,1,2007)
        receiver=Object.new
        receiver.define_singleton_method(:setInitialIndoorAirTemperature) { |value| @value=value }
        receiver.define_singleton_method(:temperature) { @value }
        super(receiver,test_weather,b,test_header,{HPXML::LocationConditionedSpace=>test_space},nil,host)
        probes << {outdoor_C:outdoor_c,ground_C:10.0,heat_C:20.0,cool_C:26.0,controls:controls,result_C:receiver.temperature}
      end
    end
    $atlas_initialization[foundation.handle.to_s]=spec.merge(numerical_verification:probes)
  end
end
Constructions.singleton_class.prepend(AtlasGroundInitialization)

def atlas_foundation(b,h,runner,r)
  Defaults.apply_site(b)
  Defaults.apply_roofs(b)
  Defaults.apply_walls(b)
  Defaults.apply_floors(runner,b)
  Defaults.apply_foundations(b)
  Defaults.apply_foundation_walls(b)
  Defaults.apply_rim_joists(b)
  Defaults.apply_slabs(b)
  Geometry.apply_foundation_and_walls_top(b)
  model=OpenStudio::Model::Model.new
  spaces={}
  $atlas_captures=[]
  $atlas_initialization={}
  $atlas_role='FoundationWallAndGroundFloor'
  Geometry.apply_foundation_walls_slabs(runner,model,spaces,nil,b,h.header,nil)
  $atlas_role='RimJoist'
  Geometry.apply_rim_joists(runner,model,spaces,b)
  ground_locations=[HPXML::LocationBasementConditioned,HPXML::LocationBasementUnconditioned,
    HPXML::LocationCrawlspaceVented,HPXML::LocationCrawlspaceUnvented,HPXML::LocationCrawlspaceConditioned,
    HPXML::LocationManufacturedHomeUnderBelly]
  originals=b.floors.to_a
  selected=originals.select { |f| !([f.interior_adjacent_to,f.exterior_adjacent_to]&ground_locations).empty? }
  b.floors.clear
  selected.each { |f| b.floors << f }
  $atlas_role='FloorOverFoundation'
  Geometry.apply_floors(runner,model,spaces,b,h.header)
  b.floors.clear
  originals.each { |f| b.floors << f }
  # Replace native handles with deterministic local identities before freezing.
  foundations=model.getFoundationKivas.sort_by(&:nameString)
  ids=foundations.each_with_index.to_h { |f,i| [f.handle.to_s,"foundation-#{i+1}"] }
  resources={}
  model.getMaterials.each do |m|
    resources[m.handle.to_s]=engine_material(m)
    resources[m.nameString]=resources[m.handle.to_s]
  end
  kiva=foundations.map do |f|
    fields=atlas_fields(f)
    fields.transform_values! { |v| resources.key?(v) ? {material:resources[v]} : v }
    {id:ids[f.handle.to_s],fields:fields,initialization:$atlas_initialization[f.handle.to_s]}
  end
  surfaces=model.getSurfaces.sort_by(&:nameString).map do |sf|
    {name:sf.nameString,surface_type:sf.surfaceType,boundary:sf.outsideBoundaryCondition,
     area_m2:sf.grossArea,vertices:sf.vertices.map { |v| [v.x,v.y,v.z] },
     host:sf.space.get.nameString,
     source_role:sf.additionalProperties.getFeatureAsString('SurfaceType').is_initialized ? sf.additionalProperties.getFeatureAsString('SurfaceType').get : nil,
     construction:sf.construction.is_initialized ? {model:'Construction',layers:sf.construction.get.to_Construction.get.layers.map { |m| engine_material(m) }} : nil,
     foundation_id:sf.adjacentFoundation.is_initialized ? ids[sf.adjacentFoundation.get.handle.to_s] : nil,
     exposed_perimeter_m:sf.surfacePropertyExposedFoundationPerimeter.is_initialized ? sf.surfacePropertyExposedFoundationPerimeter.get.totalExposedPerimeter.get : nil}
  end
  {record_id:r.fetch('record_id'),status:'recovered',surfaces:surfaces,kiva:kiva,
   kiva_settings:foundations.empty? ? nil : atlas_fields(model.getFoundationKivaSettings),
   source_foundations:b.foundations.map(&:to_h),
   source_elements:(b.foundation_walls.to_a+b.slabs.to_a+b.rim_joists.to_a+selected).map { |s| {class:s.class.name,attributes:s.to_h} },
   host_airflow:{unvented_ach:Airflow::UnventedSpaceACH,reference_height_ft:Airflow::ReferenceHeight},
   captures:$atlas_captures,warnings:runner.result.stepWarnings.to_a.map(&:to_s)}
end

code=File.read(harness)
code=code.gsub('sort_by { |s| s.additionalProperties.getFeatureAsInteger(\'Index\').get }',
  'sort_by { |s| [s.additionalProperties.getFeatureAsInteger(\'Index\').get, s.vertices.map { |v| [v.x.round(9),v.y.round(9),v.z.round(9)] }] }')
start=code.index('  Defaults.apply_site(b)')
finish=code.index("\nend\nFile.write(output",start)
raise 'Unrecognized frozen HPXML harness' if start.nil? || finish.nil?
code[start...finish]='  atlas_foundation(b,h,runner,r)'
eval(code,binding,harness)
