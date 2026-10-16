# frozen_string_literal: true
# Execute only pinned material/construction factories in isolated empty models.
require 'json'
source, input, output = ARGV
require File.join(File.expand_path(source), 'lib/openstudio-standards')
OpenStudio::Logger.instance.standardOutLogger.setLogLevel(OpenStudio::Fatal)

def read_value(object, method)
  value = object.send(method)
  value = value.get if value.respond_to?(:get)
  value
end

def layer_properties(material)
  type = %w[StandardOpaqueMaterial MasslessOpaqueMaterial AirGap SimpleGlazing StandardGlazing Gas].find do |t|
    material.send('to_' + t).is_initialized
  end
  raise 'Unsupported source native material' if type.nil?
  object = material.send('to_' + type).get
  fields = case type
  when 'StandardOpaqueMaterial'
    {'roughness'=>'roughness', 'thickness_m'=>'thickness', 'conductivity_W_m_K'=>'conductivity',
     'density_kg_m3'=>'density', 'specific_heat_J_kg_K'=>'specificHeat',
     'thermal_absorptance'=>'thermalAbsorptance', 'solar_absorptance'=>'solarAbsorptance',
     'visible_absorptance'=>'visibleAbsorptance'}
  when 'MasslessOpaqueMaterial'
    {'roughness'=>'roughness', 'resistance_m2_K_W'=>'thermalResistance',
     'thermal_absorptance'=>'thermalAbsorptance', 'solar_absorptance'=>'solarAbsorptance',
     'visible_absorptance'=>'visibleAbsorptance'}
  when 'AirGap'
    {'resistance_m2_K_W'=>'thermalResistance'}
  when 'SimpleGlazing'
    {'u_W_m2_K'=>'uFactor', 'shgc'=>'solarHeatGainCoefficient', 'visible_transmittance'=>'visibleTransmittance'}
  when 'Gas'
    {'thickness_m'=>'thickness', 'gas_type'=>'gasType'}
  when 'StandardGlazing'
    {'optical_data_type'=>'opticalDataType', 'thickness_m'=>'thickness',
     'conductivity_W_m_K'=>'thermalConductivity',
     'solar_transmittance_at_normal_incidence'=>'solarTransmittanceatNormalIncidence',
     'front_side_solar_reflectance_at_normal_incidence'=>'frontSideSolarReflectanceatNormalIncidence',
     'back_side_solar_reflectance_at_normal_incidence'=>'backSideSolarReflectanceatNormalIncidence',
     'visible_transmittance_at_normal_incidence'=>'visibleTransmittanceatNormalIncidence',
     'front_side_visible_reflectance_at_normal_incidence'=>'frontSideVisibleReflectanceatNormalIncidence',
     'back_side_visible_reflectance_at_normal_incidence'=>'backSideVisibleReflectanceatNormalIncidence',
     'infrared_transmittance_at_normal_incidence'=>'infraredTransmittanceatNormalIncidence',
     'front_side_infrared_hemispherical_emissivity'=>'frontSideInfraredHemisphericalEmissivity',
     'back_side_infrared_hemispherical_emissivity'=>'backSideInfraredHemisphericalEmissivity',
     'dirt_correction_factor_for_solar_and_visible_transmittance'=>'dirtCorrectionFactorforSolarandVisibleTransmittance',
     'solar_diffusing'=>'solarDiffusing'}
  end
  properties = {'name'=>material.nameString, 'model'=>type}
  fields.each { |key, method| properties[key] = read_value(object, method) }
  properties
end

standards = {}
results = []
inputs = JSON.parse(File.read(input))
inputs.each_with_index do |r, index|
  template = r.fetch('template')
  std = standards[template] ||= Standard.build(template)
  model = OpenStudio::Model::Model.new
  # Exact physical recipe already ambiguity-checked against the locked table.
  std.standards_data['constructions'] = [r.fetch('assembly')]
  material_rows = r.fetch('materials').select { |m| m.key?('material_type') }
  std.standards_data['materials'] = material_rows
  construction = std.model_add_construction(model, r.fetch('assembly').fetch('name'), r['properties'])
  raise 'Missing native source construction' unless construction.respond_to?(:layers)
  attrs = r['properties'] || {}
  int_film = r['properties'].nil? ? true : !!attrs['u_value_includes_interior_film_coefficient']
  ext_film = r['properties'].nil? ? true : !!attrs['u_value_includes_exterior_film_coefficient']
  films = OpenstudioStandards::Constructions.film_coefficients_r_value(
    r.fetch('assembly').fetch('intended_surface_type'), int_film, ext_film)
  native_u = nil
  native_resistances = nil
  if construction.isOpaque
    conductance = OpenstudioStandards::Constructions.construction_get_conductance(construction)
    native_resistances = construction.layers.map { |m| m.to_OpaqueMaterial.get.thermalResistance }
    native_u = 1.0 / (1.0 / conductance + films)
  elsif OpenstudioStandards::Constructions.construction_simple_glazing?(construction)
    native_u = construction.layers.first.to_SimpleGlazing.get.uFactor
  end
  results << {id:r.fetch('id'), name:construction.nameString,
              layers:construction.layers.map { |m| layer_properties(m) },
              films_m2_K_W:films, includes_interior_film:int_film, includes_exterior_film:ext_film,
              native_attained_u_W_m2_K:native_u, native_layer_resistances_m2_K_W:native_resistances}
  puts "Recovered native construction #{index + 1}/#{inputs.size}" if (index + 1) % 100 == 0
end
File.write(output, JSON.pretty_generate({runtime_version:OpenStudio.openStudioVersion, results:results}) + "\n")
