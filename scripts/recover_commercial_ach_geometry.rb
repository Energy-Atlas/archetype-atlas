# frozen_string_literal: true
# Native passive-envelope operands only; no loads, HVAC, sizing or ground solver.
require 'json'
source, input, output = ARGV
require File.join(File.expand_path(source), 'lib/openstudio-standards')
OpenStudio::Logger.instance.standardOutLogger.setLogLevel(OpenStudio::Fatal)
results = []
JSON.parse(File.read(input)).each do |r|
  template, building = r.values_at('template', 'building_type')
  std = Standard.build(template + '_' + building)
  model = std.send(:load_geometry_osm, std.geometry_file)
  model.getBuilding.setStandardsBuildingType(building)
  raise 'Geometry tweak failed' unless std.model_custom_geometry_tweaks(model, building, 'ASHRAE 169-2013-4A', std.prototype_input)
  # Source geometry contains no weather-station/height-variation or local outdoor
  # node overrides. Reject any future object instead of assuming defaults.
  forbidden = %w[OS:Site:HeightVariation OS:Site:WeatherStation OS:OutdoorAir:Node]
  raise 'Unsupported source local-weather override' if model.objects.any? { |o| forbidden.include?(o.iddObject.name) }
  model.getClimateZones.setClimateZone('ASHRAE', '4A')
  raise 'NIST recovery failed' unless OpenstudioStandards::Infiltration.model_set_nist_infiltration(model)
  multiplier_map = std.instance_variable_get(:@space_multiplier_map)
  spaces = model.getSpaces.sort_by(&:nameString).map do |s|
    mult = multiplier_map.nil? ? (s.thermalZone.is_initialized ? s.thermalZone.get.multiplier : 1) : multiplier_map.fetch(s.nameString, 1)
    {name: s.nameString, volume_m3: s.volume, multiplier: mult,
     exterior_area_m2: s.exteriorArea,
     surfaces: s.surfaces.map { |sf| {name: sf.nameString, area_m2: sf.grossArea,
       vertices_m: sf.vertices.map { |v| p = s.transformation * v; [p.x,p.y,p.z] }} }}
  end
  surfaces = model.getSurfaces
  five = surfaces.select { |s| %w[Outdoors Ground].include?(s.outsideBoundaryCondition) && %w[Wall RoofCeiling].include?(s.surfaceType) }.sum(&:grossArea)
  norm = surfaces.select { |s| s.outsideBoundaryCondition == 'Outdoors' && %w[Wall RoofCeiling].include?(s.surfaceType) }.sum(&:grossArea)
  off = model.getSpaceInfiltrationDesignFlowRates.select { |o| o.nameString.end_with?(' HVAC Off Infiltration') }
  raise 'Missing native off infiltration' if off.empty?
  rates = off.map { |o| o.flowperExteriorSurfaceArea.get }.uniq
  raise 'Unexpected varying NIST design rate' unless rates.size == 1
  coefficients = off.map { |o| {a: o.constantTermCoefficient, b: o.temperatureTermCoefficient, d: o.velocitySquaredTermCoefficient} }.uniq
  raise 'Unexpected varying NIST coefficients' unless coefficients.size == 1
  results << {id: r['id'], terrain: model.getSite.terrain,
    five_sided_area_m2: five, energyplus_normalization_area_m2: norm,
    native_flow_per_exterior_area_m_s: rates.first,
    native_off_coefficients: coefficients.first,
    nist_infiltration_space_names: off.map { |o| o.space.get.nameString }.sort, spaces: spaces}
  File.write(output, JSON.pretty_generate(results) + "\n")
  puts "Recovered #{r['id']} (#{results.size})"
end
