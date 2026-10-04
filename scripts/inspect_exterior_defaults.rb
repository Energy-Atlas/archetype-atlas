require 'json'
source,inputs,output=ARGV
source=File.expand_path(source)
require File.join(source,'resources/hpxml-measures/BuildResidentialScheduleFile/measure')
require File.join(source,'resources/hpxml-measures/BuildResidentialHPXML/resources/options')
Defaults.instance_variable_set(:@default_schedules_csv_data,Defaults.get_schedules_csv_data())
configurations=[]
JSON.parse(File.read(inputs)).each do |r|
  a=r['arguments'].transform_keys(&:to_sym)
  h=HPXML.new;h.buildings.add(building_id:r['record_id']);b=h.buildings[0]
  b.building_occupancy.number_of_residents=r['occupants']
  # Only lighting table values used: no cfa, weather, model geometry, or power guessed.
  d={};get_option_properties(d,'lighting.tsv',a.fetch(:lighting))
  {cfl:HPXML::LightingTypeCFL,lfl:HPXML::LightingTypeLFL,led:HPXML::LightingTypeLED}.each do |kind,type|
    b.lighting_groups.add(id:kind.to_s,location:HPXML::LocationExterior,lighting_type:type,
      fraction_of_units_in_location:d.fetch("lighting_exterior_fraction_#{kind}".to_sym))
  end
  b.lighting.exterior_usage_multiplier=Float(a.fetch(:exterior_lighting_usage_multiplier))
  Defaults.apply_lighting(b,nil)
  configurations<<{record_id:r['record_id'],source_building_id:r['source_building_id'],building_type:r['building_type'],
    exterior_lighting_group_count:b.lighting_groups.count,
    fraction_cfl:d[:lighting_exterior_fraction_cfl],fraction_lfl:d[:lighting_exterior_fraction_lfl],fraction_led:d[:lighting_exterior_fraction_led],
    usage_multiplier:b.lighting.exterior_usage_multiplier,
    default_shape_keys:['ExteriorWeekdayScheduleFractions','ExteriorWeekendScheduleFractions','ExteriorMonthlyScheduleMultipliers'],
    selected_application:(r['occupants']==0 ? 'reviewed_zero_occupants' : 'positive_fixed_source_default'),
    applicability:'Individual dwelling-unit exterior end use; no common-area fixture inference',
    default_fractions: {weekday:b.lighting.exterior_weekday_fractions,weekend:b.lighting.exterior_weekend_fractions,monthly:b.lighting.exterior_monthly_multipliers}}
end
shape=configurations.first[:default_fractions]
model=OpenStudio::Model::Model.new;model.getYearDescription.setCalendarYear(2007)
sch=MonthWeekdayWeekendSchedule.new(model,'exterior fixed shape proof',shape[:weekday],shape[:weekend],shape[:monthly],EPlus::ScheduleTypeLimitsFraction).schedule
wday=shape[:weekday].split(',').map(&:to_f);wkend=shape[:weekend].split(',').map(&:to_f);months=shape[:monthly].split(',').map(&:to_f)
peak=(wday+wkend).max*months.max
errors=[];values=[]
(1..365).each do |d|
  date=OpenStudio::Date.fromDayOfYear(d,2007);daily=sch.getDaySchedules(date,date)[0]
  hours=['Saturday','Sunday'].include?(date.dayOfWeek.valueName) ? wkend : wday
  (0..23).each do |hour|
    got=daily.getValue(OpenStudio::Time.new(0,hour,30,0));want=hours[hour]*months[date.monthOfYear.value-1]/peak
    errors<<(got-want).abs; values<<got
  end
end
raise 'Source schedule shape mismatch' unless errors.max<1.0e-12
raise 'Missing applications' unless configurations.size==41 && configurations.count { |r|r[:selected_application]=='positive_fixed_source_default' }==38
File.write(output,JSON.pretty_generate({status:'completed',runtime_version:OpenStudio.openStudioVersion,
  source_shape_evaluation:{year:2007,timestep_minutes:60,rows:values.size,minimum:values.min,maximum:values.max,max_error_to_source_product:errors.max,peak_divisor:peak,no_temperature_feedback:true},configurations:configurations})+"\n")
puts 'Verified 41 exact exterior-lighting configurations and 8760 pinned runtime shape values'
