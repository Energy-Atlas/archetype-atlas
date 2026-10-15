# frozen_string_literal: true
# One-day material/input smoke cells only; not archetype energy validation.
require 'json'
require 'fileutils'
input, output = ARGV
JSON.parse(File.read(input)).each do |item|
  model = OpenStudio::Model::Model.new
  model.getYearDescription.setCalendarYear(2007)
  # Fixed synthetic smoke forcing, not a claimed archetype weather benchmark.
  site = model.getSite
  site.setName('Material input smoke site')
  site.setLatitude(34)
  site.setLongitude(-118)
  site.setTimeZone(-8)
  site.setElevation(100)
  document = item.fetch('document')
  constructions = {}
  %w[ExteriorWall ExteriorRoof InteriorFloor InternalMass].each do |role|
    component = document.fetch('components').fetch(role)
    next unless component['status'] == 'ready'
    recipe = document.fetch('assemblies').fetch(component.fetch('assembly_id'))
    next unless recipe['model'] == 'opaque_layers'
    layers = OpenStudio::Model::MaterialVector.new
    recipe.fetch('layers').each_with_index do |layer, index|
      if layer['model'] == 'Material'
        m = OpenStudio::Model::StandardOpaqueMaterial.new(model)
        m.setThickness(layer.fetch('thickness_m'))
        m.setThermalConductivity(layer.fetch('conductivity_W_m_K'))
        m.setDensity(layer.fetch('density_kg_m3'))
        m.setSpecificHeat(layer.fetch('specific_heat_J_kg_K'))
      else
        m = OpenStudio::Model::MasslessOpaqueMaterial.new(model)
        m.setThermalResistance(layer.fetch('R'))
      end
      m.setName(role + ' layer ' + index.to_s)
      side = index == recipe['layers'].size - 1 ? 'interior' : 'exterior'
      properties = recipe.fetch('surface_properties').fetch(side)
      m.setRoughness(properties.fetch('roughness'))
      m.setThermalAbsorptance(properties.fetch('thermal_absorptance'))
      m.setSolarAbsorptance(properties.fetch('solar_absorptance'))
      m.setVisibleAbsorptance(properties.fetch('visible_absorptance'))
      layers << m
    end
    construction = OpenStudio::Model::Construction.new(model)
    construction.setName(role)
    construction.setLayers(layers)
    constructions[role] = construction
  end
  space = OpenStudio::Model::Space.new(model)
  zone = OpenStudio::Model::ThermalZone.new(model)
  space.setThermalZone(zone)
  faces = [
    ['Floor', 'InteriorFloor', [[0,0,0],[0,10,0],[10,10,0],[10,0,0]]],
    ['RoofCeiling', 'ExteriorRoof', [[0,0,3],[10,0,3],[10,10,3],[0,10,3]]],
    ['Wall', 'ExteriorWall', [[0,0,0],[10,0,0],[10,0,3],[0,0,3]]],
    ['Wall', 'ExteriorWall', [[10,0,0],[10,10,0],[10,10,3],[10,0,3]]],
    ['Wall', 'ExteriorWall', [[10,10,0],[0,10,0],[0,10,3],[10,10,3]]],
    ['Wall', 'ExteriorWall', [[0,10,0],[0,0,0],[0,0,3],[0,10,3]]]
  ]
  faces.each do |type, role, points|
    vertices = OpenStudio::Point3dVector.new
    points.each { |p| vertices << OpenStudio::Point3d.new(*p) }
    sf = OpenStudio::Model::Surface.new(vertices, model)
    sf.setSpace(space)
    sf.setSurfaceType(type)
    sf.setOutsideBoundaryCondition(type == 'Floor' ? 'Adiabatic' : 'Outdoors')
    sf.setSunExposure(type == 'Floor' ? 'NoSun' : 'SunExposed')
    sf.setWindExposure(type == 'Floor' ? 'NoWind' : 'WindExposed')
    # A one-storey residential profile can have no above-ground floor recipe.
    # The artificial smoke cell then uses its wall material on the adiabatic
    # closing face; this does not create or validate a foundation model.
    sf.setConstruction(constructions[role] || constructions.fetch('ExteriorWall'))
  end
  if constructions['InternalMass']
    definition = OpenStudio::Model::InternalMassDefinition.new(model)
    definition.setConstruction(constructions.fetch('InternalMass'))
    definition.setSurfaceAreaperSpaceFloorArea(document['components']['InternalMass']['quantity']['area_per_counted_floor_area'])
    mass = OpenStudio::Model::InternalMass.new(definition)
    mass.setSpace(space)
  end
  day = OpenStudio::Model::DesignDay.new(model)
  day.setName('Material smoke only')
  day.setMonth(7)
  day.setDayOfMonth(21)
  day.setDayType('SummerDesignDay')
  day.setMaximumDryBulbTemperature(32)
  day.setDailyDryBulbTemperatureRange(10)
  day.setBarometricPressure(100000)
  model.getSimulationControl.setRunSimulationforSizingPeriods(true)
  model.getSimulationControl.setRunSimulationforWeatherFileRunPeriods(false)
  model.getTimestep.setNumberOfTimestepsPerHour(4)
  dir = File.join(output, item.fetch('label'))
  FileUtils.mkdir_p(dir)
  model.save(OpenStudio::Path.new(File.join(dir, 'in.osm')), true)
  translator = OpenStudio::EnergyPlus::ForwardTranslator.new
  idf = translator.translateModel(model)
  raise translator.errors.map(&:logMessage).join('; ') unless translator.errors.empty?
  idf.save(OpenStudio::Path.new(File.join(dir, 'in.idf')), true)
  puts 'Prepared material smoke: ' + item.fetch('label')
end
