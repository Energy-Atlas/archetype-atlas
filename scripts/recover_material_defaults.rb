# frozen_string_literal: true
# Execute only constructor/default setters used by pinned Standards.Model.rb.
require 'json'
input, output = ARGV
model = OpenStudio::Model::Model.new
results = JSON.parse(File.read(input)).map do |r|
  obj = case r.fetch('model')
        when 'MasslessOpaqueMaterial' then OpenStudio::Model::MasslessOpaqueMaterial.new(model)
        when 'StandardOpaqueMaterial' then OpenStudio::Model::StandardOpaqueMaterial.new(model)
        else raise 'Unsupported default recovery model'
        end
  # Standards.Model does not set roughness for massless material, retaining SDK default.
  properties = {}
  setter_results = {}
  r.fetch('missing').each do |field|
    case field
    when 'roughness'
      raise 'Only massless constructor roughness is supported' unless r.fetch('model') == 'MasslessOpaqueMaterial'
      properties[field] = obj.roughness
    when 'thermal_absorptance', 'solar_absorptance', 'visible_absorptance'
      method = {'thermal_absorptance' => :setThermalAbsorptance, 'solar_absorptance' => :setSolarAbsorptance,
                'visible_absorptance' => :setVisibleAbsorptance}.fetch(field)
      # Source ignores the setter return value; rejection leaves the SDK default.
      setter_results[field] = obj.send(method, nil.to_f)
      value = obj.send({'thermal_absorptance' => :thermalAbsorptance,
                                   'solar_absorptance' => :solarAbsorptance,
                                   'visible_absorptance' => :visibleAbsorptance}.fetch(field))
      value = value.get if value.respond_to?(:get)
      properties[field] = Float(value)
    else raise 'Unsupported missing material field'
    end
  end
  {id: r.fetch('id'), properties: properties, setter_results: setter_results}
end
File.write(output, JSON.pretty_generate(results) + "\n")
