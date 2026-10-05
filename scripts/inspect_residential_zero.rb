# Executed pinned calculation proof; no simulation, source changes, or annual magnitude export.
require 'json'
source, inputs, output = ARGV
source = File.expand_path(source)
require File.join(source, 'resources/hpxml-measures/BuildResidentialScheduleFile/measure')
require File.join(source, 'resources/hpxml-measures/BuildResidentialHPXML/resources/options')

results=[]
JSON.parse(File.read(inputs)).select { |r| r['occupants']==0 }.each do |r|
  a=r['arguments'].transform_keys(&:to_sym)
  h=HPXML.new; h.header.eri_calculation_versions=['latest']; h.header.apply_ashrae140_assumptions=false
  h.buildings.add(building_id: r['record_id']); b=h.buildings[0]
  b.building_occupancy.number_of_residents=r['occupants']; b.building_construction.number_of_bedrooms=r['bedrooms']
  b.building_construction.residential_facility_type=a.fetch(:geometry_facility_type)
  # Execute the authoritative source CFA-bin mapping for transient lighting calculation only.
  # The atlas null CFA remains untouched. No midpoint or independent value is supplied.
  cfa=nil; cfa_bin=a.fetch(:geometry_unit_cfa_bin); unit_type=a.fetch(:geometry_facility_type)
  upstream_lines=File.readlines(File.join(source,'measures/ResStockArguments/measure.rb'))
  eval(upstream_lines[733...771].join, binding, 'pinned ResStockArguments CFA mapping', 734)
  b.building_construction.conditioned_floor_area=cfa
  b.building_construction.number_of_units=1 # defaults.rb:901-903; dwelling unit, not entire MF building
  b.water_heating.water_fixtures_usage_multiplier=Float(a.fetch(:water_fixtures_usage_multiplier))
  used={}
  {appliance_cooking_range_oven: :cooking_ranges, appliance_dishwasher: :dishwashers,
   appliance_clothes_washer: :clothes_washers,appliance_clothes_dryer: :clothes_dryers}.each do |arg,collection|
    next if a.fetch(arg)=='None'
    b.send(collection).add(id: collection.to_s); used[collection]=b.send(collection).last
  end
  calc={}
  unless used[:cooking_ranges].nil?
    calc['cooking_range']=HotWaterAndAppliances.calc_range_oven_energy(nil,b,used[:cooking_ranges],nil)
  end
  unless used[:dishwashers].nil?
    calc['dishwasher_and_hot_water_dishwasher']=HotWaterAndAppliances.calc_dishwasher_energy_gpd(nil,'latest',b,used[:dishwashers])
  end
  unless used[:clothes_washers].nil?
    calc['clothes_washer_and_hot_water_clothes_washer']=HotWaterAndAppliances.calc_clothes_washer_energy_gpd(nil,'latest',b,used[:clothes_washers])
  end
  unless used[:clothes_dryers].nil?
    calc['clothes_dryer']=HotWaterAndAppliances.calc_clothes_dryer_energy(nil,'latest',b,used[:clothes_dryers],used[:clothes_washers])
  end
  # Zero mixed draw is independent of unavailable unreported low-flow effectiveness.
  # Empty collection is evaluated first, then both limiting reported low-flow cases.
  calc['hot_water_fixtures_gpd_no_effectiveness_input']=HotWaterAndAppliances.get_fixtures_gpd('latest',b,nil)
  f=b.water_fixtures.add(id:'effectiveness-independence',water_fixture_type:HPXML::WaterFixtureTypeFaucet,count:1,low_flow:false)
  calc['hot_water_fixtures_gpd_not_low_flow']=HotWaterAndAppliances.get_fixtures_gpd('latest',b,nil)
  b.water_fixtures.last.low_flow=true
  calc['hot_water_fixtures_gpd_low_flow']=HotWaterAndAppliances.get_fixtures_gpd('latest',b,nil)
  runner=OpenStudio::Measure::OSRunner.new(OpenStudio::WorkflowJSON.new)
  model=OpenStudio::Model::Model.new
  b.plug_loads.add(id:'other',plug_load_type:HPXML::PlugLoadTypeOther,usage_multiplier:Float(a.fetch(:misc_plug_loads_other_usage_multiplier)))
  b.plug_loads.add(id:'tv',plug_load_type:HPXML::PlugLoadTypeTelevision,usage_multiplier:Float(a.fetch(:misc_plug_loads_television_usage_multiplier)))
  MiscLoads.apply_plug_loads(runner,model,{},b,h.header,nil)
  calc['plug_loads_other_and_tv_electric_equipment_count']=model.getElectricEquipments.size
  details={}; get_option_properties(details,'lighting.tsv',a.fetch(:lighting))
  [[HPXML::LocationInterior,:interior],[HPXML::LocationExterior,:exterior]].each do |location,loc|
    {cfl:HPXML::LightingTypeCFL,lfl:HPXML::LightingTypeLFL,led:HPXML::LightingTypeLED}.each do |kind,type|
      b.lighting_groups.add(id:"#{loc}-#{kind}",location:location,lighting_type:type,
        fraction_of_units_in_location:details.fetch("lighting_#{loc}_fraction_#{kind}".to_sym))
    end
  end
  b.lighting.interior_usage_multiplier=Float(a.fetch(:interior_lighting_usage_multiplier))
  b.lighting.exterior_usage_multiplier=Float(a.fetch(:exterior_lighting_usage_multiplier))
  b.lighting.garage_usage_multiplier=Float(a.fetch(:garage_lighting_usage_multiplier))
  Lighting.apply(runner,model,{},b,h.header,nil)
  calc['lighting_interior_lights_count']=model.getLightss.size
  calc['lighting_exterior_lights_count']=model.getExteriorLightss.size
  # Positive separately installed refrigeration is not switched off by zero occupancy.
  %i[appliance_refrigerator appliance_freezer].each do |arg|
    next if a.fetch(arg)=='None'
    d={};get_option_properties(d,"#{arg}.tsv",a.fetch(arg))
    collection=(arg==:appliance_refrigerator ? :refrigerators : :freezers)
    obj=b.send(collection).add(id:collection.to_s,rated_annual_kwh:d.fetch("#{arg}_rated_annual_consumption".to_sym),
      usage_multiplier:1.0)
    calc["#{collection}_rated_kwh_energy_probe"]=HotWaterAndAppliances.calc_fridge_or_freezer_energy(nil,b.send(collection).last)
  end
  raise 'Nonzero zero-occupant operational load' unless calc.reject { |k,v| k.include?('rated_kwh') }.values.flatten.all? { |v| v==0 }
  results << {record_id:r['record_id'],source_building_id:r['source_building_id'],occupants:r['occupants'],bedrooms:r['bedrooms'],
    eri_version:'latest',apply_ashrae140_assumptions:false,transient_source_default_cfa_ft2:cfa,
    zero_calculations:calc,warnings:runner.result.warnings.map(&:logMessage),
    limitations:'Calculation proofs only. CFA uses pinned source mapping transiently; atlas null retained. Low-flow endpoints are an independence check, not fixture assumptions. Refrigeration positive probe uses source rated option only; separate source usage multiplier retained in input and excluded from active magnitude outputs.'}
end
File.write(output,JSON.pretty_generate({status:'completed',runtime_version:OpenStudio.openStudioVersion,results:results})+"\n")
puts "Verified #{results.size} zero-occupant fixtures with pinned upstream routines"
