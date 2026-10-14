# frozen_string_literal: true
# Execute the pinned WSF helper on proposed reference forcing; no final policy.
require 'json'
require 'csv'
source, input, output = ARGV
require File.join(File.expand_path(source), 'resources/hpxml-measures/BuildResidentialHPXML/measure')
results = JSON.parse(File.read(input)).map do |r|
  lines = File.readlines(r.fetch('path'))
  wmo = CSV.parse_line(lines[0])[5]
  rows = lines.drop(8).map do |line|
    vals = CSV.parse_line(line)
    {'db' => Float(vals[6]), 'ws' => Float(vals[21])}
  end
  raise 'Invalid reference forcing' unless [8760, 8784].include?(rows.size) && rows.all? { |x| x['db'].abs < 100 && x['ws'] >= 0 && x['ws'] < 100 }
  weather = WeatherFile.allocate
  weather.header = Struct.new(:WMONumber).new(wmo)
  wsf = weather.send(:calc_ashrae_622_wsf, rows)
  {climate_zone: r.fetch('climate_zone'), source_map_edition: r.fetch('edition'),
   wsf: wsf, hours: rows.size,
   mean_absolute_delta_T_at_22C_K: rows.sum { |x| (22.0 - x['db']).abs } / rows.size,
   mean_wind_speed_m_s: rows.sum { |x| x['ws'] } / rows.size,
   mean_weather_wind_squared_m2_s2: rows.sum { |x| x['ws']**2 } / rows.size,
   weather_file_sha256: r.fetch('sha256')}
end
File.write(output, JSON.pretty_generate(results) + "\n")
puts "Calculated #{results.size} candidate climate references (not adopted)"
