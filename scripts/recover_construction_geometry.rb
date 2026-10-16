# frozen_string_literal: true
# Recover pressure-boundary reference operands only. No systems or simulation.
require 'json'
source, input, output, register_helper, post_hpxml = ARGV
source = File.expand_path(source) # Normalize Windows separators before source TSV globs.
require File.join(File.expand_path(source), 'measures/ResStockArguments/measure')
require File.expand_path(register_helper)
OpenStudio::Logger.instance.standardOutLogger.setLogLevel(OpenStudio::Fatal)
results = JSON.parse(File.read(input)).map do |r|
  model = OpenStudio::Model::Model.new
  processor = ResStockArguments.new
  runner = OpenStudio::Measure::OSRunner.new(OpenStudio::WorkflowJSON.new)
  registered = {}
  runner.define_singleton_method(:registerValue) { |k, v| registered[k] = v; super(k, v) }
  map = OpenStudio::Measure.convertOSArgumentVectorToMap(processor.arguments(model))
  r.fetch('arguments').each do |k, v|
    next unless map.keys.include?(k)
    arg = map[k].clone
    raise "Rejected selected argument #{k}" unless arg.setValue(v)
    map[k] = arg
  end
  raise runner.result.stepErrors.join('; ') unless processor.run(model, runner, map)
  builder = BuildResidentialHPXML.new
  bargs = builder.arguments(model)
  bmap = OpenStudio::Measure.convertOSArgumentVectorToMap(bargs)
  registered.each do |k, v|
    next unless bmap.keys.include?(k) && v != ''
    arg = bmap[k].clone
    raise "Rejected processed argument #{k}" unless arg.setValue(v)
    bmap[k] = arg
  end
  a = runner.getArgumentValues(bargs, bmap)
  Dir[File.join(source, 'resources/hpxml-measures/BuildResidentialHPXML/resources/options/*.tsv')].sort.each do |path|
    get_option_properties(a, File.basename(path), a[File.basename(path, '.tsv').to_sym])
  end
  unless builder.create_geometry_envelope(runner, model, a)
    raise "Source reference geometry failed for #{r.fetch('record_id')}: #{runner.result.stepErrors.join('; ')}"
  end
  builder.instance_variable_set(:@surface_ids, {})
  surfaces = model.getSurfaces.sort_by { |s| s.additionalProperties.getFeatureAsInteger('Index').get }
  subsurfaces = model.getSubSurfaces.sort_by { |s| s.additionalProperties.getFeatureAsInteger('Index').get }
  h = HPXML.new
  h.header.eri_calculation_versions = ['latest']
  h.header.apply_ashrae140_assumptions = false
  h.buildings.add(building_id: r.fetch('record_id'))
  b = h.buildings[0]
  builder.set_site(b, a)
  builder.set_neighbor_buildings(b, a)
  builder.set_building_construction(b, a)
  builder.set_air_infiltration_measurements(b, a)
  builder.set_roofs(b, a, surfaces)
  builder.set_rim_joists(b, model, a, surfaces)
  builder.set_walls(b, model, a, surfaces)
  builder.set_foundation_walls(b, model, a, surfaces)
  builder.set_floors(b, a, surfaces)
  builder.set_slabs(b, model, a, surfaces)
  builder.set_windows(b, model, a, subsurfaces)
  builder.set_skylights(b, a, subsurfaces)
  builder.set_doors(b, model, a, subsurfaces)
  builder.set_attics(b, a)
  builder.set_foundations(b, a)
  # Execute only the pinned stock infiltration post-processing branch.
  hpxml_bldg = b
  args = r.fetch('arguments').transform_keys(&:to_sym)
  args[:air_leakage_percent_reduction] = Float(args[:air_leakage_percent_reduction]) unless args[:air_leakage_percent_reduction].nil?
  eval(File.readlines(post_hpxml)[378...388].join, binding, 'pinned stock leakage post-processing', 379)
  Defaults.apply_building_construction(h.header, b)
  Defaults.apply_site(b)
  Defaults.apply_neighbor_buildings(b)
  Defaults.apply_infiltration(b)
  total, exterior = Defaults.get_compartmentalization_boundary_areas(b)
  measurement = Airflow.get_infiltration_measurement_of_interest(b)
  a_ext = measurement.infiltration_type == HPXML::InfiltrationTypeUnitTotal ? measurement.a_ext : 1.0
  a_ext = 1.0 if a_ext.nil? # Same detached/exterior-only branch as Airflow source.
  height = measurement.infiltration_height
  volume = measurement.infiltration_volume
  avg_height = volume / b.building_construction.conditioned_floor_area
  ach50 = measurement.air_leakage * (50.0 / measurement.house_pressure)**Airflow::InfilPressureExponent
  sla = Airflow.get_infiltration_SLA_from_ACH50(ach50, avg_height)
  weather_unit_factor = Struct.new(:data).new(Struct.new(:WSF).new(1.0))
  coefficient = Airflow.get_infiltration_ACH_from_SLA(sla, height, avg_height, weather_unit_factor) * a_ext
  {record_id: r.fetch('record_id'), geometry: {
    cfa_ft2: b.building_construction.conditioned_floor_area,
    volume_ft3: b.building_construction.conditioned_building_volume,
    infiltration_volume_ft3: volume, infiltration_height_ft: height,
    unit_height_above_grade_ft: b.building_construction.unit_height_above_grade,
    conditioned_floors_above_grade: b.building_construction.number_of_conditioned_floors_above_grade,
    source_building_floors: r.fetch('arguments').fetch('geometry_num_floors_above_grade'),
    compartment_total_area_ft2: total, compartment_exterior_area_ft2: exterior,
    a_ext: a_ext, ach50: ach50, pressure_pa: measurement.house_pressure,
    infiltration_type: measurement.infiltration_type,
    site_type: b.site.site_type, shielding: b.site.shielding_of_home,
    attached_walls: registered.fetch('geometry_attached_walls'),
    attic_type: registered.fetch('geometry_attic_type'),
    foundation_adjacency: registered.fetch('geometry_foundation_type'),
    annual_ach_per_unit_wsf: coefficient},
    neighbors: b.neighbor_buildings.map { |n| {azimuth: n.azimuth, distance_ft: n.distance, height_ft: n.height} },
    warnings: runner.result.stepWarnings.to_a}
end
File.write(output, JSON.pretty_generate({runtime_version: OpenStudio.openStudioVersion, results: results}) + "\n")
puts "Recovered pressure-boundary geometry/exposure for #{results.size} residential fixtures"
