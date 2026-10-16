# frozen_string_literal: true
# Recover selected equipment/defaults only; never generate plans or run simulation.
require 'json'
source, input, output = ARGV
source = File.expand_path(source)
require File.join(source, 'resources/hpxml-measures/BuildResidentialHPXML/measure')
Defaults.instance_variable_set(:@default_schedules_csv_data, Defaults.get_schedules_csv_data())
builder = BuildResidentialHPXML.new
results = JSON.parse(File.read(input)).map do |r|
  a = r.fetch('arguments').transform_keys(&:to_sym)
  expansions = {}
  Dir[File.join(source, 'resources/hpxml-measures/BuildResidentialHPXML/resources/options/*.tsv')].sort.each do |path|
    key = File.basename(path, '.tsv').to_sym
    next unless a.key?(key)
    before = a.dup
    get_option_properties(a, File.basename(path), a[key])
    expansions[File.basename(path)] = {selected_option: before.fetch(key),
      arguments: a.select { |k, v| !before.key?(k) || before[k] != v }}
  end
  h = HPXML.new
  h.header.eri_calculation_versions = ['latest']
  h.header.apply_ashrae140_assumptions = false
  h.buildings.add(building_id: r.fetch('record_id'))
  b = h.buildings[0]
  b.building_occupancy.number_of_residents = r.fetch('occupants')
  b.building_construction.number_of_bedrooms = r.fetch('bedrooms')
  b.building_construction.residential_facility_type = a.fetch(:geometry_facility_type)
  b.building_construction.number_of_units = 1
  b.building_construction.conditioned_floor_area = r.fetch('source_cfa_ft2')
  # Only selected adjacency categories used for equipment location, no surfaces.
  foundation = a.fetch(:geometry_foundation_type_type)
  if Float(a.fetch(:geometry_num_floors_above_grade)) > 1 && %w[Middle Top].include?(a[:geometry_unit_level])
    foundation = HPXML::FoundationTypeAboveApartment
  end
  b.foundations.add(id: 'SelectedFoundation', foundation_type: foundation)
  b.attics.add(id: 'SelectedAttic', attic_type: a.fetch(:geometry_attic_type_attic_type))
  b.walls.add(id: 'LocationOnly', interior_adjacent_to: HPXML::LocationConditionedSpace, exterior_adjacent_to: HPXML::LocationOutside)
  producers = {}
  collections = -> { b.heating_systems.to_a + b.cooling_systems.to_a + b.heat_pumps.to_a + b.water_heating_systems.to_a + b.solar_thermal_systems.to_a }
  execute_setter = lambda do |method|
    before = collections.call.map(&:object_id)
    builder.send(method, b, a)
    collections.call.each do |obj|
      producers[obj.object_id] = "BuildResidentialHPXML.#{method}" unless before.include?(obj.object_id)
    end
  end
  %i[heating_systems cooling_systems heat_pumps secondary_heating_systems].each { |key| execute_setter.call("set_#{key}") }
  execute_setter.call('set_water_heating_systems')
  # Builder solar tilt depends on a roof-pitch number; geometry default is evidence only.
  # create_geometry_envelope converts rise:12 to a slope; set_roofs restores
  # the rise before the solar method. Reproduce only that scalar operation.
  a[:geometry_roof_pitch] = Float(a.fetch(:geometry_roof_pitch).split(':').first)
  execute_setter.call('set_solar_thermal')
  Defaults.apply_water_heaters(b, 'latest', nil)
  Defaults.apply_solar_thermal_systems(b)
  equipment = []
  {heating: b.heating_systems, cooling: b.cooling_systems, heat_pump: b.heat_pumps,
   water_heater: b.water_heating_systems, solar_thermal: b.solar_thermal_systems}.each do |role, objects|
    objects.each do |obj|
      values = obj.to_h
      if role == :water_heater
        if obj.water_heater_type == HPXML::WaterHeaterTypeStorage || obj.water_heater_type == HPXML::WaterHeaterTypeTankless
          actual_volume = obj.water_heater_type == HPXML::WaterHeaterTypeTankless ? nil : Waterheater.calc_storage_tank_actual_vol(obj.tank_volume, obj.fuel_type)
          # Separate solar equipment; no solar fraction is applied twice to heater UA.
          _, ua, eta = Waterheater.disaggregate_tank_losses_and_burner_efficiency(actual_volume, obj, 0.0, r.fetch('bedrooms'))
          values[:actual_tank_volume] = actual_volume
          values[:tank_loss_coefficient] = ua
          values[:heating_input_conversion_efficiency] = eta
        elsif obj.water_heater_type == HPXML::WaterHeaterTypeHeatPump
          values[:cop] = obj.additional_properties.cop
        end
      end
      equipment << {role: role, producing_method: producers.fetch(obj.object_id), values: values}
    end
  end
  {record_id: r.fetch('record_id'), expansions: expansions, equipment: equipment,
   executed_methods: ['BuildResidentialHPXML.set_heating_systems', 'BuildResidentialHPXML.set_cooling_systems',
                      'BuildResidentialHPXML.set_heat_pumps', 'BuildResidentialHPXML.set_secondary_heating_systems',
                      'BuildResidentialHPXML.set_water_heating_systems', 'BuildResidentialHPXML.set_solar_thermal',
                      'Defaults.apply_water_heaters', 'Defaults.apply_solar_thermal_systems'],
   boundary: 'Nominal selected equipment; no HVAC sizing, performance-curve translation, surface geometry or EnergyPlus simulation.'}
end
File.write(output, JSON.pretty_generate({runtime_version: OpenStudio.openStudioVersion, results: results}) + "\n")
puts "Recovered equipment and enclosure options for #{results.size} pinned residential fixtures"
