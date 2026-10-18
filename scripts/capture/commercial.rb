# Independent native execution of pinned source methods, used only for capture.
require 'json'
require 'date'
source, input_path, output_path = ARGV
require File.join(source, 'Standards.Model.rb')
%w[create information modify parametric].each { |name| require File.join(source, 'schedules', "#{name}.rb") }
require File.join(source, 'space.rb')
require File.join(source, 'adjust_occupancy_schedule.rb')
require File.join(source, 'set_electric_equipment_bpr.rb')
require File.join(source, 'set_interior_lighting_bpr.rb')
S = OpenstudioStandards::Schedules
P = OpenstudioStandards::Space

# Capture-only memoization: unchanged native ScheduleDay timeSeries is pure.
# All annual/rule/inference/parametric callers remain the actual source code.
# Every cache miss executes the pinned daily getter; equality is independently
# checked against an uncached full-year source annual getter below.
module NativeDailyGetterCache
  def schedule_day_get_hourly_values(day, model = nil)
    model ||= day.model
    return super(day,model) if @capture_cache_disabled
    @capture_daily_cache ||= {}
    key = [model.version.str,model.getTimestep.numberOfTimestepsPerHour,
           day.interpolatetoTimestep.to_s,day.times.map(&:totalHours),day.values.to_a]
    @capture_daily_cache[key] ||= super(day,model)
    @capture_daily_cache[key].dup
  end
  def capture_uncached_hourly(schedule)
    @capture_cache_disabled = true
    schedule_ruleset_get_hourly_values(schedule)
  ensure
    @capture_cache_disabled = false
  end
end
S.singleton_class.prepend(NativeDailyGetterCache)

def make_schedule(model, source)
  standard = Standard.allocate
  rows = source.fetch('rules').map { |r| r.merge('name' => source.fetch('source_name')) }
  standard.define_singleton_method(:standards_data) { {'schedules' => rows} }
  standard.model_add_schedule(model, source.fetch('source_name'))
end

def pairs(day)
  day.times.zip(day.values).map { |time,value| [time.totalHours,value] }
end

def profiles(schedule)
  result = {'default' => pairs(schedule.defaultDaySchedule)}
  schedule.scheduleRules.each { |rule| result[rule.ruleIndex.to_s] = pairs(rule.daySchedule) }
  result
end

def days(schedule)
  S.schedule_ruleset_get_annual_days_used(schedule).transform_keys(&:to_s)
end

cases = JSON.parse(File.read(input_path)).map do |item|
  context = item.fetch('source_context')
  model = OpenStudio::Model::Model.new
  model.getYearDescription.setCalendarYear(context.fetch('year'))
  model.getTimestep.setNumberOfTimestepsPerHour(context.fetch('steps_per_hour'))
  schedule_objects = {}
  item.fetch('schedules').each { |slot,definition| schedule_objects[slot] = make_schedule(model,definition) }
  # Direct absolute People weights carry inference only; no surface/area facts.
  carrier = OpenStudio::Model::Space.new(model)
  st = OpenStudio::Model::SpaceType.new(model)
  # Standards treats a space as residential by space-type name (space.rb
  # space_residential?); a residential carrier makes inference take the
  # residential branch and invert rule days (residential-dominant buildings;
  # no packaged configuration is one today).
  residential = context.fetch('residential_carrier', false)
  st.setName(residential ? 'GuestRoom inference carrier' : 'Office inference carrier'); carrier.setSpaceType(st)
  context.fetch('occupancy_aggregation').fetch('constituents').each do |part|
    raise 'Every constituent must match the carrier residential flag' unless part.fetch('residential') == residential
    definition = OpenStudio::Model::PeopleDefinition.new(model)
    definition.setNumberofPeople(part.fetch('nominal_people'))
    people = OpenStudio::Model::People.new(definition)
    people.setSpace(carrier)
    people.setNumberofPeopleSchedule(make_schedule(model,part.fetch('schedule')))
  end
  inferred = S.model_infer_hours_of_operation_building(model)
  inference = {profiles: profiles(inferred), days_used: days(inferred), hoo: P.space_hours_of_operation(carrier)}
  original_hoo = P.space_hours_of_operation(carrier)
  getter_receipt = nil
  if item.fetch('case_id') == 'native'
    check = schedule_objects.fetch('occupancy')
    cached = S.schedule_ruleset_get_hourly_values(check)
    uncached = S.capture_uncached_hourly(check)
    raise 'Native getter cache changed full-year values' unless cached.size == 8760 && cached == uncached
    getter_receipt = {model_version: model.version.str, lexical_legacy_branch: model.version.str < '3.8.0',
                      original_cached_uncached_8760_equal: true}
  end
  original = {}
  setup = {}
  schedule_objects.each do |slot,schedule|
    original[slot] = S.schedule_ruleset_get_hourly_values(schedule)
    mode = context.fetch('slot_modes').fetch(slot)
    params = {}
    S.schedule_ruleset_get_parametric_inputs(schedule,nil,params,original_hoo,hoo_var_method: mode)
    formulas = {'default' => schedule.defaultDaySchedule.additionalProperties.getFeatureAsString('param_day_profile').get}
    schedule.scheduleRules.each { |rule| formulas[rule.ruleIndex.to_s] = rule.daySchedule.additionalProperties.getFeatureAsString('param_day_profile').get }
    setup[slot] = {formulas: formulas, profiles: profiles(schedule), days_used: days(schedule), floor: params[schedule][:floor], ceiling: params[schedule][:ceiling]}
  end
  operation = item.fetch('operating')
  vals = operation.fetch('effective_values')
  time_args = {}
  %w[weekday weekend].each do |kind|
    start = vals.fetch(kind+'_start_time').fetch('value') / 3600.0
    duration = vals.fetch(kind+'_duration').fetch('value') / 3600.0
    start_time = OpenStudio::Time.new(0,start.floor,((start-start.floor)*60).floor,0)
    end_time = start_time + OpenStudio::Time.new(0,duration.floor,((duration-duration.floor)*60).floor,0)
    (kind == 'weekday' ? ['wkdy'] : ['sat','sun']).each do |key|
      time_args[(key+'_start_time').to_sym] = start_time
      time_args[(key+'_end_time').to_sym] = end_time
    end
  end
  S.schedule_ruleset_set_hours_of_operation(inferred,**time_args)
  modified_hoo = P.space_hours_of_operation(carrier)
  pre_adjustment = {}
  schedule_objects.each do |slot,schedule|
    min_max = S.schedule_ruleset_get_min_max(schedule)
    params = {schedule => {floor: min_max['min'], ceiling: min_max['max'], target: nil, hoo_inputs: modified_hoo}}
    S.schedule_ruleset_apply_parametric_inputs(schedule,1.0/context.fetch('steps_per_hour'),true,false,params)
    pre_adjustment[slot] = {profiles: profiles(schedule), days_used: days(schedule), values: S.schedule_ruleset_get_hourly_values(schedule)}
  end
  # Exact upstream occupancy method excludes design days.
  if schedule_objects.key?('occupancy')
    schedule_ruleset_simple_value_adjust(schedule_objects.fetch('occupancy'),context.fetch('occupancy_adjustment').fetch('peak_occ_frac'),'Multiplier')
  end
  runner = OpenStudio::Measure::OSRunner.new(OpenStudio::WorkflowJSON.new)
  [['lighting','ltg_sch',SetInteriorLightingBPR],['electric_equipment','plugload_sch',SetElectricEquipmentBPR]].each do |slot,prefix,klass|
    next unless schedule_objects.key?(slot)
    schedule = schedule_objects.fetch(slot)
    wkdy = vals.fetch(prefix+'_weekday_base_peak_ratio')
    wknd = vals.fetch(prefix+'_weekend_base_peak_ratio')
    next unless wkdy.fetch('modify') || wknd.fetch('modify')
    measure = klass.new
    weekday_bases = []
    if wkdy.fetch('modify')
      weekday_bases << measure.set_sch_bpr(runner,schedule.defaultDaySchedule,wkdy.fetch('value'))
      schedule.scheduleRules.each do |rule|
        if [rule.applyMonday,rule.applyTuesday,rule.applyWednesday,rule.applyThursday,rule.applyFriday].any?
          weekday_bases << measure.set_sch_bpr(runner,rule.daySchedule,wkdy.fetch('value'))
        end
      end
    end
    if wknd.fetch('modify')
      raise 'Source weekend BPR requires weekday base' if weekday_bases.empty?
      schedule.scheduleRules.each do |rule|
        if (rule.applySaturday || rule.applySunday) && ![rule.applyMonday,rule.applyTuesday,rule.applyWednesday,rule.applyThursday,rule.applyFriday].any?
          measure.set_sch_bpr(runner,rule.daySchedule,wknd.fetch('value'),true,weekday_bases.min)
        end
      end
    end
  end
  channels = {}; special = {}; final = {}
  schedule_objects.each do |slot,schedule|
    channels[slot] = S.schedule_ruleset_get_hourly_values(schedule)
    special[slot] = {'WntrDsn' => pairs(schedule.winterDesignDaySchedule),'SmrDsn' => pairs(schedule.summerDesignDaySchedule)}
    final[slot] = {profiles: profiles(schedule),days_used: days(schedule)}
  end
  if getter_receipt
    changed = schedule_objects.fetch('occupancy')
    cached = S.schedule_ruleset_get_hourly_values(changed)
    uncached = S.capture_uncached_hourly(changed)
    raise 'Changed native getter cache changed full-year values' unless cached.size == 8760 && cached == uncached
    getter_receipt[:changed_cached_uncached_8760_equal] = true
    probe = OpenStudio::Model::ScheduleDay.new(model)
    getter_receipt[:storage_vectors] = [0.2021249999999999,0.34138927859999973,
      9.123456789012345,-0.2021249999999999,-9.123456789012345,0.875 * 0.231].map do |value|
      probe.clearValues; probe.addValue(OpenStudio::Time.new(0,24,0,0),value)
      {supplied: value, stored: probe.values[0]}
    end
    day = schedule_objects.fetch('electric_equipment').defaultDaySchedule
    getter_receipt[:off_grid_queries] = [1,9,10,11,15,19,20,21,39,40,59,60].map do |minute|
      {hour: 8, minute: minute, value: day.getValue(OpenStudio::Time.new(0,8,minute,0))}
    end
  end
  # Compact output for answer keys: final channels and the inferred hours only.
  next {case_id: item.fetch('case_id'), inference: inference, modified_hoo: modified_hoo,
        channels: channels} if context.fetch('channels_only', false)
  {case_id: item.fetch('case_id'), source_context: context, schedules: item.fetch('schedules'),
   operating: operation, inference: inference, modified_hoo: modified_hoo, setup: setup,
   original_channels: original, pre_adjustment: pre_adjustment, final: final,
   special_profiles: special, channels: channels, getter_receipt: getter_receipt}
end
File.write(output_path,JSON.generate({ruby_description: RUBY_DESCRIPTION,cases: cases})+"\n")
puts "Captured #{cases.size} commercial native cases"
