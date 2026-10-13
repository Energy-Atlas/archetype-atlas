# Execute pinned upstream methods, not the runtime's bundled standards gem.
require 'json'
require 'openstudio'
source, input_path, output_path = ARGV
class Standard
  attr_accessor :template, :standards_data
end
require File.join(source, 'lib/openstudio-standards/standards/Standards.Model.rb')
require File.join(source, 'lib/openstudio-standards/standards/Standards.WaterHeaterMixed.rb')
class ASHRAE901 < Standard; end
require File.join(source, 'lib/openstudio-standards/standards/ashrae_90_1/ashrae_90_1_2019/ashrae_90_1_2019.WaterHeaterMixed.rb')
require File.join(source, 'lib/openstudio-standards/service_water_heating/create_water_heater.rb')
results = JSON.parse(File.read(input_path)).map do |row|
  standard = row['template'] == '90.1-2019' ? ASHRAE9012019.new : Standard.new
  standard.template = row['template']
  table = JSON.parse(File.read(File.join(source, row['table_path'])))['water_heaters']
  standard.standards_data = {'water_heaters' => table}
  standard.instance_variable_set(:@instvarbuilding_type, row['building_type'])
  model = OpenStudio::Model::Model.new
  # Excluded ambient/loss behavior never enters the program representation.
  temperature = OpenStudio::Model::ScheduleConstant.new(model)
  temperature.setValue(row['temperature_degC'])
  zone = OpenStudio::Model::ThermalZone.new(model)
  heater = OpenstudioStandards::ServiceWaterHeating.create_water_heater(model,
    water_heater_capacity: OpenStudio.convert(row['capacity_Btu_h'], 'Btu/hr', 'W').get,
    water_heater_volume: OpenStudio.convert(row['volume_US_gal'], 'gal', 'm^3').get,
    water_heater_fuel: row['fuel'], service_water_temperature: row['temperature_degC'],
    service_water_temperature_schedule: temperature, water_heater_thermal_zone: zone)
  heater.setName(row['channel'] == 'booster' ? 'Booster' : row['channel'])
  before = heater.heaterThermalEfficiency.get
  capacity = OpenStudio.convert(heater.heaterMaximumCapacity.get, 'W', 'Btu/hr').get
  volume = OpenStudio.convert(heater.tankVolume.get, 'm^3', 'gal').get
  volume /= 23 if row['building_type'] == 'MidriseApartment'
  requirement = standard.water_heater_mixed_get_efficiency_requirement(heater, heater.heaterFuelType, capacity, volume)
  applied = standard.water_heater_mixed_apply_efficiency(heater)
  {'id' => row['id'], 'applied' => applied, 'factory_efficiency' => before,
   'conversion_efficiency' => applied ? heater.heaterThermalEfficiency.get : nil,
   'fuel' => heater.heaterFuelType, 'lookup_capacity_Btu_h' => capacity,
   'lookup_volume_US_gal' => volume, 'requirement' => requirement,
   'requirement_index' => table.index(requirement)}
end
File.write(output_path, JSON.pretty_generate(results) + "\n")
