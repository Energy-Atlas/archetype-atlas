# frozen_string_literal: true
# Opt-in reference capture only; never called during packaged Python generation.
require 'json'
require 'date'
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
