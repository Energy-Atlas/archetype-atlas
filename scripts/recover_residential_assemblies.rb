# frozen_string_literal: true
# Only source enclosure defaults/constructions; never HVAC, Kiva or simulation.
require 'json'
source, input, output, register_helper, post_hpxml, harness = ARGV
require File.join(File.expand_path(source), 'measures/ResStockArguments/measure')
require File.join(File.expand_path(source), 'resources/hpxml-measures/HPXMLtoOpenStudio/measure')

def source_material(m)
  if m.is_a?(GlazingMaterial)
    return {name: m.name, ufactor_Btu_h_ft2_F: m.ufactor, shgc: m.shgc}
  end
  {name: m.name, thickness_in: m.thick_in, conductivity_Btu_h_ft_F: m.k,
   density_lb_ft3: m.rho, specific_heat_Btu_lb_F: m.cp, resistance_h_ft2_F_Btu: m.rvalue,
   thermal_absorptance: m.tAbs, solar_absorptance: m.sAbs}
end

def engine_material(m)
  if m.to_StandardOpaqueMaterial.is_initialized
    m = m.to_StandardOpaqueMaterial.get
    return {name: m.name.to_s, model: 'StandardOpaqueMaterial', thickness_m: m.thickness,
      conductivity_W_m_K: m.conductivity, density_kg_m3: m.density,
      specific_heat_J_kg_K: m.specificHeat, roughness: m.roughness,
      thermal_absorptance: m.thermalAbsorptance, solar_absorptance: m.solarAbsorptance,
      visible_absorptance: m.visibleAbsorptance,
      sdk_default_flags: {thermal_absorptance: m.isThermalAbsorptanceDefaulted,
        solar_absorptance: m.isSolarAbsorptanceDefaulted, visible_absorptance: m.isVisibleAbsorptanceDefaulted}}
  end
  m = m.to_SimpleGlazing.get
  {name: m.name.to_s, model: 'SimpleGlazing', u_W_m2_K: m.uFactor,
    shgc: m.solarHeatGainCoefficient,
    visible_transmittance: m.visibleTransmittance.is_initialized ? m.visibleTransmittance.get : nil}
end

module AtlasConstructionCapture
  def create_and_assign_constructions(surfaces, model)
    native_layers = @layers_materials.map { |ms| ms.map { |m| source_material(m) } }
    effective = @layers_materials.each_with_index.filter_map do |ms, i|
      next if ms.size == 1 && ms[0].name == Constants::AirFilm
      source_material(ms.size == 1 ? ms[0] : get_parallel_material(i, @layers_names[i]))
    end
    glazing = @layers_materials.all? { |ms| ms.all? { |m| m.is_a?(GlazingMaterial) } }
    recipe = {path_fractions: @path_fracs, source_layers: native_layers,
      source_layer_names: @layers_names, effective_materials: effective,
      assembly_r_h_ft2_F_Btu: glazing ? nil : assembly_rvalue,
      caller_locations: caller_locations.filter_map { |l| l.path.include?('/resstock-') ? {path: l.path, line: l.lineno, method: l.label} : nil }}
    super
    # Some attached adiabatic source doors lose their SubSurface assignment in
    # SDK geometry validation. Construction physics is still constructed by the
    # source; retrieve that native object directly rather than repairing geometry.
    assignment = surfaces[0].construction.is_initialized
    constr = assignment ? surfaces[0].construction.get.to_Construction.get :
      Model.add_construction(model, name: @name, layers: construct_materials(model))
    $atlas_captures << {name: @name, role: $atlas_role, recipe: recipe, source_assignment_retained: assignment,
      layers: constr.layers.map { |m| engine_material(m) },
      surfaces: surfaces.map do |s|
        {id: s.name.to_s,
         area_m2: s.respond_to?(:grossArea) ? s.grossArea : s.surfaceArea.get,
         adjacent_reverse_construction: s.respond_to?(:adjacentSurface) && s.adjacentSurface.is_initialized,
         boundary: s.respond_to?(:outsideBoundaryCondition) ? s.outsideBoundaryCondition : 'InternalMass'}
      end}
  end
end
Construction.prepend(AtlasConstructionCapture)
module AtlasGeometryPrecision
  def get_roof_pitch(surfaces)
    # Only the SDK-derived angle is rounded; source material constants/formulas
    # remain full precision. This removes cross-process floating-point noise.
    Float(format('%.9g', super))
  end
end
Geometry.singleton_class.prepend(AtlasGeometryPrecision)

def atlas_enclosure(b, h, runner, r)
  $atlas_record = r.fetch('record_id')
  Defaults.apply_site(b)
  Defaults.apply_roofs(b)
  Defaults.apply_walls(b)
  Defaults.apply_floors(runner, b)
  Defaults.apply_windows(b, Constants::ERIVersions[-1])
  Defaults.apply_skylights(b)
  Defaults.apply_doors(b)
  Defaults.apply_partition_wall_mass(b)
  Geometry.apply_foundation_and_walls_top(b)
  model = OpenStudio::Model::Model.new
  spaces = {}
  $atlas_captures = []
  # Foundation-dependent floor interfaces belong to the deferred ground axis.
  ground_locations = [HPXML::LocationBasementConditioned, HPXML::LocationBasementUnconditioned,
    HPXML::LocationCrawlspaceVented, HPXML::LocationCrawlspaceUnvented,
    HPXML::LocationCrawlspaceConditioned, HPXML::LocationManufacturedHomeUnderBelly]
  deferred = b.foundation_walls.map { |x| {id: x.id, role: 'FoundationWall'} } +
    b.slabs.map { |x| {id: x.id, role: 'Slab'} } + b.rim_joists.map { |x| {id: x.id, role: 'RimJoist'} }
  floors = b.floors.select { |f| ([f.interior_adjacent_to, f.exterior_adjacent_to] & ground_locations).empty? }
  (b.floors.to_a - floors).each { |f| deferred << {id: f.id, role: 'FloorOverFoundation',
    interior: f.interior_adjacent_to, exterior: f.exterior_adjacent_to} }
  context = (b.roofs.to_a + b.walls.to_a + b.floors.to_a + b.windows.to_a + b.skylights.to_a + b.doors.to_a).map do |s|
    {id: s.id, class: s.class.name, attributes: s.to_h}
  end
  $atlas_role = 'Roof'
  Geometry.apply_roofs(runner, model, spaces, b, h.header)
  $atlas_role = 'Wall'
  Geometry.apply_walls(runner, model, spaces, b, h.header)
  # Execute the exact floor branch on a temporary collection; restore source floors
  # before calculating ordinary inferred interstory floor area.
  originals = b.floors.to_a
  b.floors.clear
  floors.each { |f| b.floors << f }
  $atlas_role = 'FloorCeiling'
  Geometry.apply_floors(runner, model, spaces, b, h.header)
  b.floors.clear
  originals.each { |f| b.floors << f }
  $atlas_role = 'OrdinaryInteriorFloor'
  Geometry.apply_conditioned_floor_area(model, spaces, b)
  # No glazing shading schedules are needed to recover the glazing materials.
  # Use the source geometry branch, capturing engine assignments, with shading
  # suppressed solely because it is a separate non-material consumer operation.
  Constructions.singleton_class.class_eval do
    alias_method :atlas_saved_shading, :apply_window_skylight_shading
    define_method(:apply_window_skylight_shading) { |*_args| }
  end
  $atlas_role = 'Window'
  Geometry.apply_windows(runner, model, spaces, b, h.header)
  $atlas_role = 'Door'
  Geometry.apply_doors(model, spaces, b)
  $atlas_role = 'Skylight'
  Geometry.apply_skylights(runner, model, spaces, b, h.header)
  Constructions.singleton_class.class_eval do
    alias_method :apply_window_skylight_shading, :atlas_saved_shading
    remove_method :atlas_saved_shading
  end
  $atlas_role = 'InteriorPartition'
  Geometry.create_or_get_space(model, spaces, HPXML::LocationConditionedSpace, b)
  mat = Material.InteriorFinishMaterial(b.partition_wall_mass.interior_finish_type, b.partition_wall_mass.interior_finish_thickness)
  Constructions.apply_partition_walls(model, 'PartitionWallConstruction', mat,
    b.partition_wall_mass.area_fraction * b.building_construction.conditioned_floor_area, spaces)
  {record_id: r.fetch('record_id'), assemblies: $atlas_captures,
   deferred_elements: deferred, source_context: context,
   conditioned_floor_area_ft2: b.building_construction.conditioned_floor_area,
   partition_wall_mass: b.partition_wall_mass.to_h, warnings: runner.result.stepWarnings.to_a.map(&:to_s)}
end

# Reuse the reviewed argument/default/HPXML fixture harness verbatim up to the
# source building-construction defaults. The original file remains immutable.
code = File.read(harness)
# Source indices tie for generated surfaces. Stable geometry-only tie-breaking
# changes generated names, not physics, argument selection or geometry creation.
code = code.gsub("sort_by { |s| s.additionalProperties.getFeatureAsInteger('Index').get }",
  "sort_by { |s| [s.additionalProperties.getFeatureAsInteger('Index').get, s.vertices.map { |v| [v.x.round(9), v.y.round(9), v.z.round(9)] }] }")
start = code.index('  Defaults.apply_site(b)')
finish = code.index("\nend\nFile.write(output", start)
raise 'Unrecognized geometry harness boundary' if start.nil? || finish.nil?
code[start...finish] = "  atlas_enclosure(b, h, runner, r)"
code = code.sub('Recovered pressure-boundary geometry/exposure', 'Recovered above-ground ordered assemblies')
eval(code, binding, harness)
