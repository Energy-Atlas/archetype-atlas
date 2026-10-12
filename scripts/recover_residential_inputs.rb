# frozen_string_literal: true
# Targeted execution of checksum-locked ResStock program routines; no simulation.
require 'json'
source, input, output, post_hpxml = ARGV
source = File.expand_path(source)
require File.join(source, 'resources/hpxml-measures/BuildResidentialHPXML/measure')
Defaults.instance_variable_set(:@default_schedules_csv_data, Defaults.get_schedules_csv_data())
builder = BuildResidentialHPXML.new
results = []
JSON.parse(File.read(input)).each do |r|
  a = r.fetch('arguments').transform_keys(&:to_sym)
  a[:misc_pool] = 'None' if a.fetch(:misc_has_pool) == 'false' # ResStockArguments.run
  if Float(a.fetch(:geometry_num_floors_above_grade)) > 1 && %w[Middle Top].include?(a[:geometry_unit_level])
    a[:geometry_foundation_type] = 'Above Apartment' # ResStockArguments.run adiabatic floor branch
  end
  # Only expand exact selected option tables; omitted properties remain nil for
  # upstream default methods, rather than taking unrelated sample-model defaults.
  keys = %i[appliance_clothes_washer appliance_clothes_dryer appliance_dishwasher appliance_refrigerator appliance_extra_refrigerator appliance_freezer appliance_cooking_range_oven lighting misc_plug_loads misc_television ceiling_fans dhw_fixtures dhw_water_heater geometry_garage_type geometry_foundation_type misc_well_pump misc_grill misc_fireplace misc_gas_lighting misc_pool misc_permanent_spa]
  keys.each { |key| get_option_properties(a, "#{key}.tsv", a.fetch(key)) }
  h = HPXML.new
  h.header.eri_calculation_versions = ['latest']
  h.header.apply_ashrae140_assumptions = false
  h.buildings.add(building_id: r['record_id'])
  b = h.buildings[0]
  b.building_occupancy.number_of_residents = r['occupants']
  b.building_construction.number_of_bedrooms = r['bedrooms']
  b.building_construction.residential_facility_type = a.fetch(:geometry_facility_type)
  b.building_construction.number_of_units = 1
  cfa_bin = a.fetch(:geometry_unit_cfa_bin); unit_type = a.fetch(:geometry_facility_type)
  cfa = nil
  eval(File.readlines(File.join(source, 'measures/ResStockArguments/measure.rb'))[733...771].join, binding, 'pinned CFA mapping', 734)
  raise 'Unknown CFA mapping' if cfa.nil?
  b.building_construction.conditioned_floor_area = cfa
  locations = [HPXML::LocationConditionedSpace]
  gfa = a.fetch(:geometry_garage_type_width) * a.fetch(:geometry_garage_type_depth)
  locations << HPXML::LocationGarage if gfa > 0
  foundation = a.fetch(:geometry_foundation_type_type)
  locations << HPXML::LocationBasementUnconditioned if foundation == HPXML::FoundationTypeBasementUnconditioned
  locations << HPXML::LocationBasementConditioned if foundation == HPXML::FoundationTypeBasementConditioned
  locations.each { |loc| b.walls.add(id: loc, interior_adjacent_to: loc, exterior_adjacent_to: HPXML::LocationOutside) }
  %i[clothes_washer clothes_dryer dishwasher refrigerator extra_refrigerator freezer cooking_range_oven ceiling_fans misc_plug_loads_television misc_plug_loads_other misc_plug_loads_well_pump misc_fuel_loads_grill misc_fuel_loads_lighting misc_fuel_loads_fireplace pool permanent_spa water_fixtures].each { |key| builder.send("set_#{key}", b, a) }
  Defaults.apply_appliances(b, 'latest', nil)
  Defaults.apply_plug_loads(b, nil)
  Defaults.apply_fuel_loads(b, nil)
  Defaults.apply_pools_and_permanent_spas(b, nil)
  # Execute exact stock post-processing, including distinct primary/extra
  # refrigeration and freezer calibration factors.
  hpxml_bldg = b
  args = a.transform_values { |v| v }
  args.keys.grep(/usage_multiplier/).each { |key| args[key] = Float(args[key]) unless args[key].nil? }
  eval(File.readlines(post_hpxml)[295...356].join, binding, 'pinned ResStockArgumentsPostHPXML usage calibration', 296)
  loads = []
  add_energy = lambda do |name, kwh, sens, lat, fuel, host, method|
    loads << {end_use: name, annual_kwh: kwh, fuel: fuel, host: host, heat_fractions: {radiant: 0.6 * sens, latent: lat, lost: 1 - sens - lat}, method: method}
  end
  add_water = lambda do |name, gpd, temp, method|
    loads << {end_use: name, daily_gallons: gpd, host: HPXML::LocationConditionedSpace, target_temperature_degC: UnitConversions.convert(temp, 'F', 'C'), method: method}
  end
  water_temp = a[:dhw_water_heater_temperature] || Defaults.get_water_heater_temperature('latest')
  b.clothes_washers.each do |obj|
    kwh, sens, lat, gpd = HotWaterAndAppliances.calc_clothes_washer_energy_gpd(nil, 'latest', b, obj)
    add_energy.call('clothes_washer', kwh, sens, lat, 'electricity', obj.location, 'HotWaterAndAppliances.calc_clothes_washer_energy_gpd')
    add_water.call('hot_water_clothes_washer', gpd, water_temp, 'HotWaterAndAppliances.calc_clothes_washer_energy_gpd')
  end
  b.dishwashers.each do |obj|
    kwh, sens, lat, gpd = HotWaterAndAppliances.calc_dishwasher_energy_gpd(nil, 'latest', b, obj)
    add_energy.call('dishwasher', kwh, sens, lat, 'electricity', obj.location, 'HotWaterAndAppliances.calc_dishwasher_energy_gpd')
    add_water.call('hot_water_dishwasher', gpd, water_temp, 'HotWaterAndAppliances.calc_dishwasher_energy_gpd')
  end
  {clothes_dryer: b.clothes_dryers, cooking_range: b.cooking_ranges}.each do |name, objects|
    objects.each do |obj|
      if name == :clothes_dryer
        kwh, therm, sens, lat = HotWaterAndAppliances.calc_clothes_dryer_energy(nil, 'latest', b, obj, b.clothes_washers[0])
        method = 'HotWaterAndAppliances.calc_clothes_dryer_energy'
      else
        kwh, therm, sens, lat = HotWaterAndAppliances.calc_range_oven_energy(nil, b, obj, b.ovens[0])
        method = 'HotWaterAndAppliances.calc_range_oven_energy'
      end
      add_energy.call(name, kwh, sens, lat, 'electricity', obj.location, method)
      if obj.fuel_type != HPXML::FuelTypeElectricity
        add_energy.call(name, UnitConversions.convert(therm, 'therm', 'kWh'), sens, lat, obj.fuel_type, obj.location, method)
        loads[-1][:annual_therm] = therm
      end
    end
  end
  {refrigerator: b.refrigerators, freezer: b.freezers}.each do |name, objects|
    objects.each do |obj|
      kwh, sens, lat = HotWaterAndAppliances.calc_fridge_or_freezer_energy(nil, obj)
      actual_name = name == :refrigerator && obj.primary_indicator == false ? :extra_refrigerator : name
      add_energy.call(actual_name, kwh, sens, lat, 'electricity', obj.location, 'HotWaterAndAppliances.calc_fridge_or_freezer_energy')
    end
  end
  b.plug_loads.each do |obj|
    name = {HPXML::PlugLoadTypeOther => 'plug_loads_other', HPXML::PlugLoadTypeTelevision => 'plug_loads_tv', HPXML::PlugLoadTypeWellPump => 'plug_loads_well_pump'}.fetch(obj.plug_load_type)
    kwh = r['occupants'] == 0 ? 0 : obj.kwh_per_year * obj.usage_multiplier
    add_energy.call(name, kwh, obj.frac_sensible, obj.frac_latent, 'electricity', HPXML::LocationConditionedSpace, 'Defaults.apply_plug_loads; MiscLoads.apply_plug_loads')
  end
  b.fuel_loads.each do |obj|
    name = {HPXML::FuelLoadTypeGrill => 'fuel_loads_grill', HPXML::FuelLoadTypeLighting => 'fuel_loads_lighting', HPXML::FuelLoadTypeFireplace => 'fuel_loads_fireplace'}.fetch(obj.fuel_load_type)
    therm = r['occupants'] == 0 ? 0 : obj.therm_per_year * obj.usage_multiplier
    add_energy.call(name, UnitConversions.convert(therm, 'therm', 'kWh'), obj.frac_sensible, obj.frac_latent, obj.fuel_type, HPXML::LocationConditionedSpace, 'Defaults.apply_fuel_loads; MiscLoads.apply_fuel_loads')
    loads[-1][:annual_therm] = therm
  end
  {pool: b.pools, permanent_spa: b.permanent_spas}.each do |name, objects|
    objects.each do |obj|
      add_energy.call("#{name}_pump", obj.pump_kwh_per_year * obj.pump_usage_multiplier, 0, 0, 'electricity', HPXML::LocationConditionedSpace, 'Defaults.apply_pools_and_permanent_spas; MiscLoads.apply_pool_or_permanent_spa_pump')
      next if obj.heater_type == HPXML::TypeNone
      energy = obj.heater_load_value * obj.heater_usage_multiplier
      fuel = 'electricity'
      if obj.heater_load_units == HPXML::UnitsThermPerYear
        energy = UnitConversions.convert(energy, 'therm', 'kWh')
        fuel = HPXML::FuelTypeNaturalGas # Exact translator fuel, retained separately from stock label
      end
      add_energy.call("#{name}_heater", energy, 0, 0, fuel, HPXML::LocationConditionedSpace, 'Defaults.apply_pools_and_permanent_spas; MiscLoads.apply_pool_or_permanent_spa_heater')
    end
  end
  %i[interior exterior garage].each do |loc|
    area = loc == :garage ? gfa : cfa
    fractions = %i[cfl lfl led].map { |kind| a.fetch("lighting_#{loc}_fraction_#{kind}".to_sym) }
    kwh = Lighting.send("calc_#{loc}_energy", 'latest', area, *fractions)
    kwh = 0 if r['occupants'] == 0 || area == 0
    kwh *= Float(a.fetch("#{loc}_lighting_usage_multiplier".to_sym))
    host = {interior: HPXML::LocationConditionedSpace, exterior: HPXML::LocationOutside, garage: HPXML::LocationGarage}.fetch(loc)
    loads << {end_use: "lighting_#{loc}", annual_kwh: kwh, fuel: 'electricity', host: host, method: "Lighting.calc_#{loc}_energy; Lighting.apply", heat_fractions: {radiant: 0.6, visible: 0.2, return_air: 0}}
  end
  if b.ceiling_fans.size > 0
    obj = b.ceiling_fans[0]
    count = obj.count || Defaults.get_ceiling_fan_count(r['bedrooms'])
    power = obj.label_energy_use || (obj.efficiency.nil? ? Defaults.get_ceiling_fan_power : 3000.0 / obj.efficiency)
    weather = WeatherFile.new(epw_path: r.fetch('epw_path'), runner: nil)
    months = Defaults.get_ceiling_fan_months(weather)
    kwh = r['occupants'] == 0 ? 0 : count * power * 10.5 * 365 / 1000 * months.sum / 12.0
    loads << {end_use: 'ceiling_fan', annual_kwh: kwh, fuel: 'electricity', host: HPXML::LocationConditionedSpace, method: 'HVAC.apply_ceiling_fans; Defaults.get_ceiling_fan_count; Defaults.get_ceiling_fan_power; Defaults.get_ceiling_fan_months', heat_fractions: {radiant: 0.558, latent: 0, lost: 0}}
  end
  add_water.call('hot_water_fixtures', HotWaterAndAppliances.get_fixtures_gpd('latest', b, nil), 105.0, 'HotWaterAndAppliances.get_fixtures_gpd')
  gain, hours, sensible, latent = Defaults.get_occupancy_values()
  controls = {activity_W_person: UnitConversions.convert(gain, 'Btu/hr', 'W'), people_radiant_fraction: 0.558 * sensible, people_sensible_fraction: sensible}
  results << {record_id: r['record_id'], loads: loads, controls: controls, source_cfa_ft2: cfa, source_garage_area_ft2: gfa, expanded_arguments: a, water_supply_degF: water_temp}
end
File.write(output, JSON.pretty_generate({runtime_version: OpenStudio.openStudioVersion, results: results}) + "\n")
puts "Recovered #{results.size} dwelling program inputs from pinned source methods"
