# Native residential/non-residential design people on real prototype geometry, used only for capture.
# For each case: load the template's geometry, give every listed space its People
# (floor area x definition density, attached to the space as the builder assumes),
# then total space.numberOfPeople x space.multiplier by OpenstudioStandards
# space_residential?, exactly as parametric.rb model_infer_hours_of_operation_building does.
require 'json'
source, input_path, output_path = ARGV
require File.join(source, 'Standards.Model.rb')
%w[create information modify parametric].each { |name| require File.join(source, 'schedules', "#{name}.rb") }
require File.join(source, 'space.rb')
P = OpenstudioStandards::Space

cases = JSON.parse(File.read(input_path)).map do |item|
  loaded = OpenStudio::OSVersion::VersionTranslator.new.loadModel(OpenStudio::Path.new(item.fetch('geometry_path')))
  raise "Geometry missing: #{item.fetch('geometry_path')}" unless loaded.is_initialized
  model = loaded.get
  raise 'Geometry already contains People' unless model.getPeoples.empty?
  densities = item.fetch('densities')
  model.getSpaces.each do |space|
    next unless space.spaceType.is_initialized
    density = densities[space.spaceType.get.standardsSpaceType.to_s]
    next if density.nil?
    definition = OpenStudio::Model::PeopleDefinition.new(model)
    definition.setPeopleperSpaceFloorArea(density)
    OpenStudio::Model::People.new(definition).setSpace(space)
  end
  totals = {'residential' => 0.0, 'non_residential' => 0.0}
  spaces = []
  model.getSpaces.sort.each do |space|
    residential = P.space_residential?(space)
    people = space.numberOfPeople
    totals[residential ? 'residential' : 'non_residential'] += people * space.multiplier
    spaces << {name: space.name.get, residential: residential, people: people, multiplier: space.multiplier} if people > 0
  end
  {case_id: item.fetch('case_id'), totals: totals, spaces: spaces}
end
File.write(output_path, JSON.generate({ruby_description: RUBY_DESCRIPTION, openstudio_version: OpenStudio.openStudioVersion, cases: cases}) + "\n")
puts "Captured #{cases.size} occupancy dominance cases"
