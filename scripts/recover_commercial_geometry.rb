# frozen_string_literal: true
# Load source geometry and execute lookup queries; never construct HVAC/ground models.
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
  climate = 'ASHRAE 169-2013-4A' # Geometry-only evaluation context; no weather assigned.
  raise 'Geometry tweak failed' unless std.model_custom_geometry_tweaks(model, building, climate, std.prototype_input)
  multiplier_map = std.instance_variable_get(:@space_multiplier_map)
  spaces = model.getSpaces.sort_by(&:nameString).map do |s|
    mult = multiplier_map.nil? ? (s.thermalZone.is_initialized ? s.thermalZone.get.multiplier : 1) : multiplier_map.fetch(s.nameString, 1)
    type = s.spaceType.is_initialized ? s.spaceType.get : nil
    z = s.transformation * OpenStudio::Point3d.new(0, 0, 0)
    verts = s.surfaces.flat_map { |sf| sf.vertices.map { |v| (s.transformation * v).z } }
    {name: s.nameString, floor_area_m2: s.floorArea, volume_m3: s.volume,
     multiplier: mult, part_of_total_floor_area: s.partofTotalFloorArea,
     z_min_m: verts.min, z_max_m: verts.max,
     standards_building_type: type && type.standardsBuildingType.is_initialized ? type.standardsBuildingType.get : nil,
     standards_space_type: type && type.standardsSpaceType.is_initialized ? type.standardsSpaceType.get : nil,
     outdoor_wall_area_m2: s.surfaces.select { |sf| sf.outsideBoundaryCondition == 'Outdoors' && sf.surfaceType == 'Wall' }.sum(&:grossArea),
     outdoor_roof_area_m2: s.surfaces.select { |sf| sf.outsideBoundaryCondition == 'Outdoors' && sf.surfaceType == 'RoofCeiling' }.sum(&:grossArea),
     outdoor_floor_area_m2: s.surfaces.select { |sf| sf.outsideBoundaryCondition == 'Outdoors' && sf.surfaceType == 'Floor' }.sum(&:grossArea)}
  end
  lookup = %w[SmallOffice MediumOffice LargeOffice SmallOfficeDetailed MediumOfficeDetailed LargeOfficeDetailed].include?(building) ? building : std.model_get_lookup_name(building)
  queries = [{building_type: lookup, space_type: nil, is_residential: 'No', context: 'building_default'}]
  spaces.each do |s|
    queries << {building_type: s[:standards_space_type] == 'Attic' ? '' : s[:standards_building_type],
                space_type: s[:standards_space_type], is_residential: 'No', context: 'space_type'}
  end
  # Also retain compatibility lookups for legacy generic Office packages.
  queries << {building_type: std.model_get_lookup_name(building), space_type: nil, is_residential: 'No', context: 'compatibility_lookup'}
  # Reproduce only the source story-level lookup decision, not construction creation.
  if lookup == 'SmallHotel'
    model.getBuildingStorys.sort_by(&:nameString).each do |story|
      next if story.nameString == 'AtticStory'
      exterior_area = 0.0
      residential_area = 0.0
      story.spaces.each do |space|
        next if space.exteriorWallArea.zero?
        type = space.spaceType.get
        name = type.standardsSpaceType.is_initialized ? type.standardsSpaceType.get : nil
        data = std.standards_lookup_table_first(table_name: 'space_types', search_criteria: {
          'template' => template, 'building_type' => lookup, 'space_type' => name})
        raise 'Missing story occupancy classification' if data.nil?
        exterior_area += space.floorArea
        residential_area += space.floorArea if data['is_residential'] == 'Yes'
      end
      if exterior_area > 0 && residential_area / exterior_area >= 0.5
        queries << {building_type: lookup, space_type: nil, is_residential: 'Yes',
                    context: 'story_override', story: story.nameString,
                    spaces: story.spaces.map(&:nameString).sort}
      end
    end
  end
  selected = queries.uniq.filter_map do |q|
    criteria = {'template' => template, 'climate_zone_set' => std.model_find_climate_zone_set(model, climate),
                'building_type' => q[:building_type], 'space_type' => q[:space_type], 'is_residential' => q[:is_residential]}
    found = std.model_find_object(std.standards_data['construction_sets'], criteria)
    found ||= std.model_find_object(std.standards_data['construction_sets'], criteria.reject { |k,_| k == 'is_residential' })
    found && {query: q, source_set: found}
  end
  results << {id: template + '/' + building, template: template, building_type: building,
    geometry_file: 'data/' + std.geometry_file, geometry_context: climate, spaces: spaces,
    selected_sets: selected.map { |s| s[:source_set] }.uniq, queries: selected,
    prototype_input: std.prototype_input.slice('geometry_osm', 'building_type', 'template'),
    nist_inferred_type: OpenstudioStandards::Infiltration.model_infer_nist_building_type(model),
    source_site_terrain: model.getSite.terrain,
    site_terrain_defaulted: model.getSite.isTerrainDefaulted,
    geometry_tweak_source: std.method(:model_custom_geometry_tweaks).source_location}
  File.write(output, JSON.pretty_generate({runtime_version: OpenStudio.openStudioVersion, results: results}) + "\n")
end
File.write(output, JSON.pretty_generate({runtime_version: OpenStudio.openStudioVersion, results: results}) + "\n")
puts "Recovered #{results.size} commercial reference geometries"
