require 'json'
source,output=ARGV
require File.join(File.expand_path(source),'lib/openstudio-standards')
results=[]
cases={'SmallHotel'=>['DOE Ref Pre-1980','DOE Ref 1980-2004','90.1-2007','90.1-2013','90.1-2019'],'HighriseApartment'=>['90.1-2007','90.1-2013','90.1-2019']}
cases.each do |building,templates|
 templates.each do |template|
  std=Standard.build(template+'_'+building)
  model=std.send(:load_geometry_osm,std.geometry_file)
  model.getBuilding.setStandardsBuildingType(building)
  result={'building_type'=>building,'template'=>template,'climate_zone'=>'ASHRAE 169-2013-4A','phases'=>[],'errors'=>[]}
  begin
   [['loads',lambda{std.model_add_loads(model)}],['thermal_zones',lambda{std.model_create_thermal_zones(model,std.instance_variable_get(:@space_multiplier_map))}],['hvac',lambda{std.model_add_hvac(model,building,result['climate_zone'],std.prototype_input)}],['custom_hvac_tweaks',lambda{std.model_custom_hvac_tweaks(model,building,result['climate_zone'],std.prototype_input)}],['transfer_air',lambda{std.model_add_transfer_air(model)}]].each do |name,fn|
    fn.call;result['phases'] << name
   end
  rescue => e
   result['errors'] << {'exception'=>e.class.to_s,'message'=>e.message,'backtrace'=>e.backtrace.take(10)}
  end
  result['spaces']=model.getSpaces.sort.select{|s|s.spaceType.is_initialized && (building=='SmallHotel' ? ['Elec/MechRoom','ElevatorCore','ElevatorCore4'].include?(s.spaceType.get.standardsSpaceType.get) : ['Corridor','Corridor_topfloor'].include?(s.spaceType.get.standardsSpaceType.get))}.map do |s|
   z=s.thermalZone.get;t=z.thermostatSetpointDualSetpoint.is_initialized ? z.thermostatSetpointDualSetpoint.get : nil
   {'space'=>s.nameString,'source_space_type'=>s.spaceType.get.standardsSpaceType.get,'zone'=>z.nameString,'zone_spaces'=>z.spaces.map(&:nameString),'thermostat'=>t && t.nameString,'heating_schedule'=>t && t.heatingSetpointTemperatureSchedule.is_initialized ? t.heatingSetpointTemperatureSchedule.get.nameString : nil,'cooling_schedule'=>t && t.coolingSetpointTemperatureSchedule.is_initialized ? t.coolingSetpointTemperatureSchedule.get.nameString : nil,'equipment'=>z.equipment.map{|e|[e.iddObjectType.valueName,e.nameString]},'air_loops'=>z.airLoopHVACs.map(&:nameString),'ideal_loads'=>z.useIdealAirLoads,'zone_mixing'=>model.getZoneMixings.select{|x|x.zone==z || (x.sourceZone.is_initialized && x.sourceZone.get==z)}.map(&:nameString)}
  end
  results << result
  File.write(output,JSON.pretty_generate(results))
  puts [building,template,result['phases'],result['errors']].inspect
 end
end
