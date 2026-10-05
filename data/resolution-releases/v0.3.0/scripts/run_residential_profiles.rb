# frozen_string_literal: true
# Schedule-only execution of checksum-locked upstream code. No EnergyPlus run.
require 'json'
require 'date'
require 'csv'
source, input_path, output = ARGV
require File.join(source, 'resources/hpxml-measures/BuildResidentialScheduleFile/measure')
require File.join(source, 'measures/ResStockArguments/measure')
Dir.mkdir(output) unless Dir.exist?(output)
JSON.parse(File.read(input_path)).each do |item|
  runner = OpenStudio::Measure::OSRunner.new(OpenStudio::WorkflowJSON.new)
  hpxml = HPXML.new
  hpxml.header.sim_calendar_year = item['year']
  hpxml.header.timestep = item['timestep_minutes']
  hpxml.buildings.add(building_id: item['record_id'])
  bldg = hpxml.buildings[0]
  bldg.building_occupancy.number_of_residents = item['occupants']
  bldg.building_construction.number_of_bedrooms = item['bedrooms']
  a = item['arguments']
  { 'appliance_dishwasher' => :dishwashers, 'appliance_clothes_washer' => :clothes_washers,
    'appliance_clothes_dryer' => :clothes_dryers, 'appliance_cooking_range_oven' => :cooking_ranges,
    'ceiling_fans' => :ceiling_fans }.each do |arg, collection|
    raise "Missing exact presence input #{arg}" if a[arg].nil?
    bldg.send(collection).add(id: collection.to_s) unless a[arg] == 'None'
  end
  # Explicit source usage bindings establish presence; amplitudes are metadata,
  # not multipliers of the normalized schedule shape.
  { 'misc_plug_loads_other_usage_multiplier' => 'other',
    'misc_plug_loads_television_usage_multiplier' => 'TV other' }.each do |arg, type|
    raise "Missing exact plug load input #{arg}" if a[arg].nil?
    bldg.plug_loads.add(id: type, plug_load_type: type) if Float(a[arg]) > 0
  end
  if item['selected_options']['Geometry Garage'] != 'None'
    bldg.walls.add(id: 'source-garage-presence', interior_adjacent_to: HPXML::LocationGarage,
                   exterior_adjacent_to: HPXML::LocationOutside)
  end
  weather = WeatherFile.new(epw_path: item['epw_path'], runner: runner)
  schedules_path = File.join(output, item['record_id'] + '.csv')
  status = 'executed_stochastic'
  if item['occupants'] == 0
    # Honor BuildResidentialScheduleFile.run's explicit skip. Other loads remain unknown.
    CSV.open(schedules_path, 'w') do |csv|
      csv << ['occupants']
      (Calendar.num_days_in_year(item['year']) * 24).times { csv << [0] }
    end
    status = 'upstream_zero_occupants_skip_with_explicit_zero_occupancy'
  else
    args = { geometry_num_occupants: item['occupants'],
             resources_path: File.join(source, 'resources/hpxml-measures/BuildResidentialScheduleFile/resources'),
             latitude: item['latitude'], longitude: item['longitude'],
             time_zone_utc_offset: item['time_zone_utc_offset'] }
    columns = ScheduleGenerator.export_columns.reject { |c| c.start_with?('electric_vehicle') }
    generator = ScheduleGenerator.new(runner: runner, hpxml_bldg: bldg, state: item['state'],
      column_names: columns, random_seed: item['seed'], minutes_per_step: item['timestep_minutes'],
      steps_in_day: 24, total_days_in_year: Calendar.num_days_in_year(item['year']),
      sim_year: item['year'], sim_start_day: DateTime.new(item['year'], 1, 1), debug: false, append_output: false)
    raise 'Upstream generation failed' unless generator.create(args: args, weather: weather)
    raise 'Upstream export failed' unless generator.export(schedules_path: schedules_path)
  end
  # Execute both upstream offset translation and HVAC conflict correction. The
  # temporary OS model exists only to evaluate the upstream ScheduleRulesets.
  control_args = {}
  %w[heating cooling].each do |mode|
    period = a.fetch("hvac_control_#{mode}_season_period")
    raise "Unsupported source season #{period}" unless period == 'Jan 1 - Dec 31'
    %w[weekday weekend].each do |day|
      prefix = "hvac_control_#{mode}_#{day}_setpoint"
      base = Float(a.fetch(prefix + '_temp'))
      magnitude = Float(a.fetch(prefix + '_offset_magnitude'))
      directions = a.fetch(prefix + '_schedule').split(',').map { |v| Float(v) }
      raise 'Expected 24 offset directions' unless directions.size == 24
      values = ResStockArguments.new.modify_setpoint_schedule([base] * 24, magnitude, directions)
      control_args[(day + '_' + mode + '_setpoints').to_sym] = values.join(',')
    end
  end
  control_args.merge!(id: 'source-control', seasons_heating_begin_month: 1, seasons_heating_begin_day: 1,
    seasons_heating_end_month: 12, seasons_heating_end_day: 31, seasons_cooling_begin_month: 1,
    seasons_cooling_begin_day: 1, seasons_cooling_end_month: 12, seasons_cooling_end_day: 31)
  bldg.hvac_controls.add(**control_args)
  model = OpenStudio::Model::Model.new
  model.getYearDescription.setCalendarYear(item['year'])
  space = OpenStudio::Model::Space.new(model)
  zone = OpenStudio::Model::ThermalZone.new(model)
  space.setThermalZone(zone)
  HVAC.apply_setpoints(runner, model, weather, { HPXML::LocationConditionedSpace => space }, bldg, hpxml.header, nil)
  thermostat = zone.thermostatSetpointDualSetpoint.get
  heating = thermostat.heatingSetpointTemperatureSchedule.get.to_ScheduleRuleset.get
  cooling = thermostat.coolingSetpointTemperatureSchedule.get.to_ScheduleRuleset.get
  table = CSV.read(schedules_path)
  table[0] += ['heating_setpoint', 'cooling_setpoint']
  (1..Calendar.num_days_in_year(item['year'])).each do |d|
    date = OpenStudio::Date.fromDayOfYear(d, item['year'])
    hs = heating.getDaySchedules(date, date)[0]
    cs = cooling.getDaySchedules(date, date)[0]
    (0..23).each do |h|
      time = OpenStudio::Time.new(0, h, 30, 0)
      table[(d - 1) * 24 + h + 1] += [hs.getValue(time).round(9), cs.getValue(time).round(9)]
    end
  end
  CSV.open(schedules_path, 'w') { |csv| table.each { |row| csv << row } }
  messages = runner.result.warnings.map(&:logMessage)
  File.write(File.join(output, item['record_id'] + '.execution.json'),
             JSON.pretty_generate({ status: status, warnings: messages }) + "\n")
  puts "#{item['record_id']}: #{status}"
end
