# frozen_string_literal: true
# Opt-in reference capture only; never called during packaged Python generation.
require 'json'
require 'date'
if ARGV[0] == '--residential'
  require 'ostruct'
  _, source, input_path, output_path = ARGV
  require File.join(source, 'resources/hpxml-measures/BuildResidentialScheduleFile/measure')
  raise 'Unexpected Ruby runtime' unless RUBY_VERSION == '3.2.2'
  module ActivityCapture
    def simulate_occupant_activities
      @capturing_activity = true
      @capture_types = []
      @capture_decisions = []
      result = super
      @capture_traces = result.map { |matrix| matrix.to_a.map { |row| row.index(1) } }
      @capturing_activity = false
      result
    end
    def fill_activity_duration_precomputed_vals(map, type)
      @capture_types << type if @capturing_activity
      super
    end
    def sample_activity_duration(prng, map, type, state, daytype, hour, precomputed = nil)
      result = super
      @capture_decisions << [state, result] if @capturing_activity
      result
    end
    def generate_sink_schedule(traces)
      state, left, = @prngs[:main].send(:marshal_dump)
      @capture_result = {resident_states: @capture_traces, occupant_types: @capture_types,
        decisions: @capture_decisions, unit_offset_minutes: @random_offset,
        main_state: {algorithm: 'ruby-3.2.2-mt19937-v1', seed: @random_seed,
          state: 624.times.map { |i| (state >> (32 * i)) & 0xffffffff }, index: 625 - left},
        enduse_states: @prngs.reject { |key, _| key == :main }.to_h { |key,rng|
          words, remaining, seed = rng.send(:marshal_dump)
          [key,{algorithm: 'ruby-3.2.2-mt19937-v1', seed: seed,
            state: 624.times.map { |i| (words >> (32 * i)) & 0xffffffff }, index: 625 - remaining}]
        }, channels: @schedules.dup}
      throw :captured_shapes
    end
    attr_reader :capture_result
  end
  ScheduleGenerator.prepend(ActivityCapture)
  cases = JSON.parse(File.read(input_path)).map do |item|
    runner = OpenStudio::Measure::OSRunner.new(OpenStudio::WorkflowJSON.new)
    hpxml = HPXML.new
    hpxml.buildings.add(building_id: item.fetch('case_id'))
    bldg = hpxml.buildings[0]
    installed = item.fetch('inputs').fetch('installed')
    {'dishwasher' => :dishwashers, 'clothes_washer' => :clothes_washers,
     'clothes_dryer' => :clothes_dryers, 'cooking_range' => :cooking_ranges,
     'ceiling_fan' => :ceiling_fans}.each do |key, collection|
      bldg.send(collection).add(id: key) if installed.fetch(key)
    end
    {'plug_loads_other' => 'other', 'plug_loads_tv' => 'TV other'}.each do |key,type|
      bldg.plug_loads.add(id: key, plug_load_type: type) if installed.fetch(key)
    end
    if installed.fetch('garage')
      bldg.walls.add(id: 'garage', interior_adjacent_to: HPXML::LocationGarage,
        exterior_adjacent_to: HPXML::LocationOutside)
    end
    inputs = item.fetch('inputs')
    year = inputs.fetch('year')
    temperatures = item.fetch('drybulb_C')
    start = 0
    monthly = Calendar.num_days_in_months(year).map do |days|
      values = temperatures[start, days * 24]; start += days * 24
      UnitConversions.convert(values.sum / values.size, 'C', 'F')
    end
    weather = OpenStruct.new(data: OpenStruct.new(MonthlyAvgDrybulbs: monthly))
    generator = ScheduleGenerator.new(runner: runner, hpxml_bldg: bldg, state: inputs.fetch('state'),
      column_names: ScheduleGenerator.export_columns, random_seed: item.fetch('unit_seed'), minutes_per_step: 60,
      steps_in_day: 24, total_days_in_year: 365, sim_year: year, sim_start_day: DateTime.new(year,1,1),
      debug: false, append_output: false)
    args = {geometry_num_occupants: inputs.fetch('residents'),
      resources_path: File.join(source,'resources/hpxml-measures/BuildResidentialScheduleFile/resources'),
      latitude: inputs.fetch('latitude'), longitude: inputs.fetch('longitude'),
      time_zone_utc_offset: inputs.fetch('time_zone_utc_offset')}
    if inputs.fetch('residents') == 0
      result = {resident_states: [], occupant_types: [], decisions: [], unit_offset_minutes: nil,
        main_state: nil, enduse_states: {}, channels: {'occupants' => [0.0] * 8760}, status: 'upstream_zero_residents_skip'}
    else
      catch(:captured_shapes) { generator.create(args: args, weather: weather) }
      result = generator.capture_result.merge(status: 'executed_source_through_coordinated_shapes')
    end
    result.merge(case_id: item.fetch('case_id'), inputs: inputs, unit_seed: item.fetch('unit_seed'),
      fan_months: monthly.map { |v| v > 63.0 ? 1 : 0 })
  end
  File.write(output_path, JSON.generate({ruby_description: RUBY_DESCRIPTION, cases: cases}) + "\n")
  puts "Captured #{cases.size} independent residential activity/shape cases"
  exit
end
input_path, standards_method, output_path = ARGV
input = JSON.parse(File.read(input_path))
raise 'Unexpected Ruby runtime' unless RUBY_VERSION == '3.2.2'
require standards_method

random_vectors = input.fetch('seeds').map do |seed|
  rng = Random.new(seed)
  initial_dump = rng.send(:marshal_dump)
  draws = []
  limits = [nil, 2**32, 97, nil, 1, 3, 2**32 + 1, 2**64 - 1, 2**72 + 3, nil, 65537]
  75.times do
    limits.each do |limit|
      value = limit.nil? ? rng.rand : rng.rand(limit)
      draws << {limit: limit, value: value}
    end
  end
  state, left, = rng.send(:marshal_dump)
  restored = Marshal.load(Marshal.dump(rng))
  restoration_draws = [rng.rand, rng.rand(97), rng.rand(2**72 + 3)]
  raise 'Ruby state restoration failure' unless restoration_draws == [restored.rand, restored.rand(97), restored.rand(2**72 + 3)]
  {seed: seed, draws: draws, initial_state: {state: 624.times.map { |i| (initial_dump[0] >> (32 * i)) & 0xffffffff }, index: 624},
   final_state: {state: 624.times.map { |i| (state >> (32 * i)) & 0xffffffff }, index: 625 - left},
   restoration_draws: restoration_draws}
end

enduse_vectors = input.fetch('seeds').map do |seed|
  allocator = Random.new(seed)
  {unit_seed: seed, slots: %w[hygiene dishwasher clothes_washer clothes_dryer ev cooking].map { |key| {key: key, seed: allocator.rand(2**32)} }}
end

rule_vectors = input.fetch('schedules').flat_map do |source|
  [[], ['2007-01-01']].map do |holidays|
    model = OpenStudio::Model::Model.new
    model.getYearDescription.setCalendarYear(2007)
    standard = Standard.allocate
    rows = source.fetch('rules').map { |r| r.merge('name' => source.fetch('source_name')) }
    standard.define_singleton_method(:standards_data) { {'schedules' => rows} }
    schedule = standard.model_add_schedule(model, source.fetch('source_name'))
    values = []
    365.times do |i|
      date = OpenStudio::Date.fromDayOfYear(i + 1, 2007)
      profile = holidays.include?((Date.new(2007,1,1)+i).iso8601) ? schedule.defaultDaySchedule : schedule.getDaySchedules(date,date)[0]
      24.times { |h| values << profile.getValue(OpenStudio::Time.new(0,h,30,0)) }
    end
    special = {}
    {'WntrDsn' => schedule.winterDesignDaySchedule, 'SmrDsn' => schedule.summerDesignDaySchedule}.each do |key,profile|
      next unless source['rules'].any? { |r| r['day_types'].split('|').include?(key) }
      special[key] = 24.times.map { |h| profile.getValue(OpenStudio::Time.new(0,h,30,0)) }
    end
    {schedule_id: source.fetch('id'), year: 2007, holidays: holidays, values: values, special_profiles: special,
     default_profile: 24.times.map { |h| schedule.defaultDaySchedule.getValue(OpenStudio::Time.new(0,h,30,0)) }}
  end
end
File.write(output_path,JSON.generate({ruby_description: RUBY_DESCRIPTION, random_vectors: random_vectors, enduse_vectors: enduse_vectors, rule_vectors: rule_vectors}) + "\n")
puts "Captured #{random_vectors.size} independent Ruby RNG vectors and #{rule_vectors.size} OpenStudio rule vectors"
