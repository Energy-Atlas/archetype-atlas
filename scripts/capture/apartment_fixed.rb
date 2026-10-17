# Opt-in native experiment: exact c8 construction/helpers + distinct0.8.6 getter.
# No geometry/prototype/thermal/ResStock execution or runtime admission.
require 'json'
require 'digest'
require 'date'
source, input_path, output_path = ARGV
require File.join(source, 'standards/standard.rb')
require File.join(source, 'standards/Standards.Model.rb')
require File.join(source, 'schedules/create.rb')
require File.join(source, 'schedules/information.rb')
require File.join(source, 'standards/Standards.ServiceWaterHeating.rb')
require File.join(source, 'service_water_heating/create_water_use.rb')
S = OpenstudioStandards::Schedules

def pairs(day)
  day.times.zip(day.values).map { |t, v| [t.totalHours, v] }
end

def receipt(schedule, original_rows = [])
  model = schedule.model
  first = OpenStudio::Date.new(OpenStudio::MonthOfYear.new(1), 1, 2007)
  last = OpenStudio::Date.new(OpenStudio::MonthOfYear.new(12), 31, 2007)
  profiles = {'default' => pairs(schedule.defaultDaySchedule)}
  selectors = %w[Monday Tuesday Wednesday Thursday Friday Saturday Sunday]
  rule_rows = original_rows.select { |r| r.fetch('value').fetch('day_types').split('|').any? { |d| %w[Wkdy Wknd Mon Tue Wed Thu Fri Sat Sun].include?(d) } }.reverse
  order = schedule.scheduleRules.each_with_index.map do |rule, i|
    profiles[rule.ruleIndex.to_s] = pairs(rule.daySchedule)
    start = rule.startDate.get; finish = rule.endDate.get
    {source_index: rule_rows.fetch(i).fetch('locator').split('/').last.to_i,
     start_date: format('%02d-%02d', start.monthOfYear.value, start.dayOfMonth),
     end_date: format('%02d-%02d', finish.monthOfYear.value, finish.dayOfMonth),
     day_selectors: selectors.select { |d| rule.public_send('apply' + d) }.map { |d| d[0,3] }}
  end
  # All annual arrays execute the actual original getter, without memoization.
  {profiles: profiles, rule_order: order,
   day_rule_indices: schedule.getActiveRuleIndices(first, last).to_a,
   special_profiles: {'WntrDsn' => pairs(schedule.winterDesignDaySchedule),
                      'SmrDsn' => pairs(schedule.summerDesignDaySchedule)},
   values: S.schedule_ruleset_get_hourly_values(schedule)}
end

def model_2007
  model = OpenStudio::Model::Model.new
  model.getYearDescription.setCalendarYear(2007)
  model.getTimestep.setNumberOfTimestepsPerHour(6)
  model
end

input = JSON.parse(File.read(input_path))
raise 'Exact fixed capture calendar required' unless input.fetch('reference_calendar') == {'year'=>2007, 'clock'=>'local_standard_time', 'holidays'=>[]}
rows = input.fetch('schedules').flat_map { |s| s.fetch('rows').map { |r| r.fetch('value') } }
standard = Standard.allocate
standard.standards_data = {'schedules' => rows}
model = model_2007
schedules = input.fetch('schedules').map do |item|
  original = item.fetch('source').fetch('value')
  if item.fetch('construction_kind') == 'original_c8_named_ruleset'
    schedule = standard.model_add_schedule(model, original.fetch('source_name'))
  elsif item.fetch('construction_kind') == 'reviewed_zero_overlay_native_representation'
    raise 'Original reviewed zero overlay/provenance required' unless item.fetch('rows').empty? && !item.fetch('overlay_provenance').empty? && original.fetch('rules').size == 1 && original.fetch('rules')[0].fetch('values') == [0]
    schedule = S.create_constant_schedule_ruleset(model, 0, name:original.fetch('source_name'))
  else
    raise 'Unsupported source construction identity'
  end
  raise 'Original named Ruleset missing' if schedule.to_ScheduleRuleset.empty?
  schedule = schedule.to_ScheduleRuleset.get
  receipt(schedule, item.fetch('rows')).merge(id: item.fetch('id'), source_rows: item.fetch('rows'), programme_ids: item.fetch('programme_ids'),
    construction_kind:item.fetch('construction_kind'), overlay_provenance:item.fetch('overlay_provenance'),
    original_explicit_special_day_selectors:item.fetch('original_explicit_special_day_selectors'))
end

water_paths = input.fetch('water_paths').map do |item|
  row = item.fetch('row').fetch('value')
  model = model_2007
  standard = Standard.allocate
  standard.standards_data = {'schedules' => rows, 'space_types' => [row]}
  # Explicit exact source row/table input; actual c8 lookup methods execute.
  standard.instance_variable_set(:@template, row.fetch('template'))
  lookup = standard.model_get_lookup_name(row.fetch('building_type'))
  criteria = {'template'=>row.fetch('template'), 'building_type'=>lookup, 'space_type'=>row.fetch('space_type')}
  raise 'Actual original lookup selects another row' unless criteria.all? { |k,v| row.fetch(k)==v } && standard.standards_lookup_table_first(table_name:'space_types', search_criteria:criteria)==row
  probes = input.fetch('synthetic_floor_areas_m2').map do |area|
    # setFloorArea is an explicit synthetic caller area, never a prototype fact.
    space = OpenStudio::Model::Space.new(model)
    raise 'Explicit synthetic floor area rejected' unless space.setFloorArea(area)
    raise 'Explicit synthetic multiplier1 required' unless space.multiplier == 1
    space.setName('Synthetic caller area ' + area.to_s + 'm2')
    st = OpenStudio::Model::SpaceType.new(model)
    st.setStandardsBuildingType(row.fetch('building_type'))
    st.setStandardsSpaceType(row.fetch('space_type'))
    space.setSpaceType(st)
    fixture = standard.model_add_swh_end_uses_by_space(model, nil, space, is_flow_per_area:true)
    raise 'Actual original per-area helper failed' if fixture.nil?
    definition = fixture.waterUseEquipmentDefinition
    water = fixture.flowRateFractionSchedule.get.to_ScheduleRuleset.get
    water_item = input.fetch('schedules').find { |s| s.fetch('id') == item.fetch('schedule_id') }
    {floor_area_m2: space.floorArea, space_multiplier: space.multiplier,
     is_flow_per_area: true, lookup_building_type: lookup, lookup_criteria: criteria,
     source_density_gal_h_ft2: row.fetch('service_water_heating_peak_flow_per_area'),
     native_area_ft2: OpenStudio.convert(space.floorArea, 'm^2', 'ft^2').get,
     source_temperature_F: row.fetch('service_water_heating_target_temperature'),
     native_temperature_operand_C: OpenStudio.convert(row.fetch('service_water_heating_target_temperature'), 'F', 'C').get,
     source_system_type: row.fetch('service_water_heating_system_type'),
     native_peak_flow_m3_s: definition.peakFlowRate,
     flow_schedule_name: water.name.get, flow_values: receipt(water, water_item.fetch('rows'))[:values],
     attached_space: fixture.space.empty? ? nil : fixture.space.get.name.get,
     controls: {target_temperature: receipt(definition.targetTemperatureSchedule.get.to_ScheduleRuleset.get),
                sensible_fraction: receipt(definition.sensibleFractionSchedule.get.to_ScheduleRuleset.get),
                latent_fraction: receipt(definition.latentFractionSchedule.get.to_ScheduleRuleset.get)}}
  end
  item.merge('probes' => probes)
end
output = {schema_version:'1.0.0', input_sha256:Digest::SHA256.file(input_path).hexdigest,
  source_members:input.fetch('source_members'), reference_calendar:input.fetch('reference_calendar'),
  model_version:model.version.str, legacy_round5:model.version.str < '3.8.0', steps_per_hour:6,
  ruby_description:RUBY_DESCRIPTION, schedules:schedules, water_paths:water_paths}
File.write(output_path, JSON.generate(output))
puts JSON.generate({fixed_rulesets:schedules.size, water_paths:water_paths.size, synthetic_area_probes:water_paths.sum { |p| p.fetch('probes').size }})
