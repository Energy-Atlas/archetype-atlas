# frozen_string_literal: true
# Geometry, native program keys and source internal-mass inventory only.
require 'json'
source, input, output = ARGV
require File.join(File.expand_path(source), 'lib/openstudio-standards')
OpenStudio::Logger.instance.standardOutLogger.setLogLevel(OpenStudio::Fatal)

def optional(o)
  o.is_initialized ? o.get : nil
end

def mass_layers(construction)
  return nil unless construction.is_initialized && construction.get.to_Construction.is_initialized
  construction.get.to_Construction.get.layers.map do |m|
    return nil unless m.to_StandardOpaqueMaterial.is_initialized
    p = m.to_StandardOpaqueMaterial.get
    {name: p.nameString, thickness_m: p.thickness, conductivity_W_m_K: p.conductivity,
     density_kg_m3: p.density, specific_heat_J_kg_K: p.specificHeat,
     thermal_absorptance: p.thermalAbsorptance, solar_absorptance: p.solarAbsorptance,
     visible_absorptance: p.visibleAbsorptance, roughness: p.roughness}
  end
end

results = []
JSON.parse(File.read(input)).each do |r|
  template, building = r.values_at('template', 'building_type')
  std = Standard.build(template + '_' + building)
  model = std.send(:load_geometry_osm, std.geometry_file)
  model.getBuilding.setStandardsBuildingType(building)
  raise 'Source geometry tweak failed' unless std.model_custom_geometry_tweaks(model, building, 'ASHRAE 169-2013-4A', std.prototype_input)
  mults = std.instance_variable_get(:@space_multiplier_map)
  rows = {}
  model.getSpaceTypes.sort_by(&:nameString).each do |type|
    rows[type.nameString] = std.space_type_get_standards_data(type)
    # Native thermostat rules are evaluated only to recover the source test for
    # adding furnishings. No annual schedule arrays or systems are generated.
    std.space_type_apply_thermostat_schedules(type)
  end
  model.getSpaces.each do |space|
    next unless space.spaceType.is_initialized
    thermostat = model.getThermostatSetpointDualSetpointByName(space.spaceType.get.nameString + ' Thermostat')
    next unless thermostat.is_initialized
    zone = space.thermalZone.is_initialized ? space.thermalZone.get : OpenStudio::Model::ThermalZone.new(model)
    space.setThermalZone(zone) unless space.thermalZone.is_initialized
    zone.setThermostatSetpointDualSetpoint(thermostat.get)
  end
  std.model_add_internal_mass(model, building)
  spaces = model.getSpaces.sort_by(&:nameString).map do |s|
    mult = mults.nil? ? (s.thermalZone.is_initialized ? s.thermalZone.get.multiplier : 1) : mults.fetch(s.nameString, 1)
    type = s.spaceType.is_initialized ? s.spaceType.get : nil
    surfaces = s.surfaces.sort_by(&:nameString).map do |sf|
      openings = sf.subSurfaces.sort_by(&:nameString).map do |ss|
        {id: ss.nameString, type: ss.subSurfaceType, area_m2: ss.grossArea,
         multiplier: ss.multiplier}
      end
      {id: sf.nameString, type: sf.surfaceType, boundary: sf.outsideBoundaryCondition,
       gross_area_m2: sf.grossArea, net_area_m2: sf.netArea,
       adjacent_id: sf.adjacentSurface.is_initialized ? sf.adjacentSurface.get.nameString : nil,
       openings: openings}
    end
    mass = s.internalMass.sort_by(&:nameString).map do |obj|
      d = obj.internalMassDefinition
      {id: obj.nameString, direct_area_m2: optional(d.surfaceArea),
       area_per_floor_area: optional(d.surfaceAreaperSpaceFloorArea),
       area_per_person_m2: optional(d.surfaceAreaperPerson),
       layers: mass_layers(d.construction)}
    end
    {name: s.nameString, floor_area_m2: s.floorArea, volume_m3: s.volume,
     multiplier: mult, counted_floor_area: s.partofTotalFloorArea,
     story: s.buildingStory.is_initialized ? s.buildingStory.get.nameString : nil,
     native_program: type.nil? ? nil : rows[type.nameString],
     source_space_type_name: type.nil? ? nil : type.nameString,
     heated: OpenstudioStandards::Space.space_heated?(s),
     cooled: OpenstudioStandards::Space.space_cooled?(s),
     surfaces: surfaces, internal_mass: mass}
  end
  results << {id: template + '/' + building, template: template, building_type: building,
              geometry_file: 'data/' + std.geometry_file, spaces: spaces}
  File.write(output, JSON.pretty_generate({runtime: OpenStudio.openStudioVersion, results: results}) + "\n")
  puts "Recovered weighting profile #{results.size}: #{template}/#{building}"
end
