# frozen_string_literal: true
# Small synthetic method-input cells, not archetype or zoning-error validation.
require 'json'
require 'fileutils'
input,output=ARGV

def material(model,record)
  p=record.fetch('properties')
  m=if record['model']=='StandardOpaqueMaterial'
    x=OpenStudio::Model::StandardOpaqueMaterial.new(model)
    {'setThickness'=>'thickness_m','setThermalConductivity'=>'conductivity_W_m_K','setDensity'=>'density_kg_m3','setSpecificHeat'=>'specific_heat_J_kg_K'}.each { |s,k| raise "Rejected #{k}" unless x.send(s,p.fetch(k)) }
    x
  elsif record['model']=='MasslessOpaqueMaterial'
    x=OpenStudio::Model::MasslessOpaqueMaterial.new(model)
    raise 'Rejected resistance' unless x.setThermalResistance(p.fetch('resistance_m2_K_W'))
    x
  else
    raise 'Unsupported smoke material '+record['model']
  end
  {'setRoughness'=>'roughness','setThermalAbsorptance'=>'thermal_absorptance','setSolarAbsorptance'=>'solar_absorptance','setVisibleAbsorptance'=>'visible_absorptance'}.each { |s,k| raise "Rejected #{k}" unless m.send(s,p.fetch(k)) }
  m
end

def construction(model,document,aid)
  return $smoke_constructions[aid] if $smoke_constructions.key?(aid)
  a=document.fetch('assemblies').fetch(aid)
  result=case a['model']
  when 'FFactorGroundFloorConstruction'
    x=OpenStudio::Model::FFactorGroundFloorConstruction.new(model)
    x.setFFactor(a.fetch('f_W_m_K'));x.setArea(100);x.setPerimeterExposed($smoke_perimeter)
    x
  when 'CFactorUndergroundWallConstruction'
    x=OpenStudio::Model::CFactorUndergroundWallConstruction.new(model)
    x.setCFactor(a.fetch('c_W_m2_K'));x.setHeight(3);x
  else
    x=OpenStudio::Model::Construction.new(model)
    layers=OpenStudio::Model::MaterialVector.new
    a.fetch('layers').each { |l| layers << material(model,document.fetch('materials').fetch(l.fetch('material_id'))) }
    raise 'Rejected native layers' unless x.setLayers(layers)
    x
  end
  $smoke_constructions[aid]=result
end

def dimension(value,document)
  return value if value.is_a?(Numeric)
  result=if value['geometry_input']
    {'wall_height_above_grade_m'=>0.0,'foundation_wall_height_m'=>3.0}.fetch(value['geometry_input'])
  elsif value['material_thickness_id']
    document['materials'].fetch(value['material_thickness_id'])['properties'].fetch('thickness_m')
  else
    document['assemblies'].fetch(value.fetch('assembly_thickness_id'))['layers'].sum { |l| document['materials'].fetch(l['material_id'])['properties'].fetch('thickness_m') }
  end
  result*value.fetch('scale',1.0)+value.fetch('offset_m',0.0)
end

JSON.parse(File.read(input)).each do |item|
  d=item.fetch('document');model=OpenStudio::Model::Model.new
  $smoke_constructions={}
  model.getYearDescription.setCalendarYear(2007)
  site=item.fetch('weather_site')
  model.getSite.setLatitude(site['latitude']);model.getSite.setLongitude(site['longitude']);model.getSite.setTimeZone(site['time_zone']);model.getSite.setElevation(site['elevation_m'])
  $smoke_perimeter=item.fetch('perimeter_m',40.0)
  ground_rule=item.fetch('ground_rule');method=d['foundation_ground']['methods'].fetch(ground_rule.fetch('ground_method_id'))
  ground=construction(model,d,ground_rule['assembly_id'])
  closing=item.fetch('closing_document') # Declared test-cell closing faces, not a catalogue fallback.
  shell_rule=closing['components']['ExteriorWall']['assignments'].first
  shell=construction(model,closing,shell_rule.fetch('assembly_id'))
  kiva=nil
  if method['model']=='Kiva'
    kiva=OpenStudio::Model::FoundationKiva.new(model)
    params=method['parameters'];settings=d['foundation_ground']['model_parameters'].fetch(method['model_parameters_id'])
    soil=d['materials'].fetch(settings['soil_material_id'])['properties']
    s=model.getFoundationKivaSettings
    {'setSoilConductivity'=>'conductivity_W_m_K','setSoilDensity'=>'density_kg_m3','setSoilSpecificHeat'=>'specific_heat_J_kg_K'}.each { |setter,key| s.send(setter,soil.fetch(key)) }
    {'setGroundSolarAbsorptivity'=>'ground_solar_absorptivity','setGroundThermalAbsorptivity'=>'ground_thermal_absorptivity','setGroundSurfaceRoughness'=>'ground_surface_roughness_m',
      'setFarFieldWidth'=>'far_field_width_m','setDeepGroundBoundaryCondition'=>'deep_ground_boundary_condition','setDeepGroundDepth'=>'deep_ground_depth_m',
      'setMinimumCellDimension'=>'minimum_cell_dimension_m','setMaximumCellGrowthCoefficient'=>'maximum_cell_growth_coefficient','setSimulationTimestep'=>'simulation_timestep'}.each { |setter,key| s.send(setter,settings.fetch(key)) }
    kiva.setWallHeightAboveGrade(dimension(params.fetch('wall_height_above_grade'),d))
    kiva.setWallDepthBelowSlab(params.fetch('wall_depth_below_slab_m'))
    kiva.setInitialIndoorAirTemperature(item.fetch('initial_temperature_C'))
    {'interior_horizontal'=>'InteriorHorizontal','interior_vertical'=>'InteriorVertical','exterior_horizontal'=>'ExteriorHorizontal','exterior_vertical'=>'ExteriorVertical'}.each do |key,stem|
      ins=params[key+'_insulation'];next if ins.nil?
      kiva.send('set'+stem+'InsulationMaterial',material(model,d['materials'].fetch(ins['material_id'])))
      kiva.send('set'+stem+'InsulationDepth',dimension(ins['depth_m'],d)) if ins['depth_m']
      kiva.send('set'+stem+'InsulationWidth',dimension(ins['width_m'],d)) if ins['width_m']
    end
    params.fetch('custom_blocks',[]).each { |b| kiva.addCustomBlock(material(model,d['materials'].fetch(b['material_id'])),dimension(b['depth_m'],d),dimension(b['x_m'],d),dimension(b['z_m'],d)) }
  end
  model.getSiteGroundTemperatureFCfactorMethod.setAllMonthlyTemperatures(Array.new(12,18.0))
  model.getSiteGroundTemperatureBuildingSurface.setAllMonthlyTemperatures(Array.new(12,18.0))
  space=OpenStudio::Model::Space.new(model);zone=OpenStudio::Model::ThermalZone.new(model);space.setThermalZone(zone)
  z=item['walled_kiva'] ? -3 : 0
  faces=[['Floor',[[0,0,z],[0,10,z],[10,10,z],[10,0,z]]],
    ['RoofCeiling',[[0,0,z+3],[10,0,z+3],[10,10,z+3],[0,10,z+3]]],
    ['Wall',[[0,0,z],[10,0,z],[10,0,z+3],[0,0,z+3]]],
    ['Wall',[[10,0,z],[10,10,z],[10,10,z+3],[10,0,z+3]]],
    ['Wall',[[10,10,z],[0,10,z],[0,10,z+3],[10,10,z+3]]],
    ['Wall',[[0,10,z],[0,0,z],[0,0,z+3],[0,10,z+3]]]]
  faces.each_with_index do |(type,points),index|
    points=points.rotate(-1) if type=='Wall' # Upper-left first, matching GlobalGeometryRules and native C-factor height.
    v=OpenStudio::Point3dVector.new;points.each { |p| v << OpenStudio::Point3d.new(*p) }
    sf=OpenStudio::Model::Surface.new(v,model);sf.setName('Smoke surface '+index.to_s);sf.setSpace(space);sf.setSurfaceType(type)
    sf.setOutsideBoundaryCondition('Outdoors');sf.setConstruction(shell)
    sf.setSunExposure('NoSun');sf.setWindExposure('NoWind')
    if type=='Floor' && method['model']!='CFactor'
      sf.setConstruction(ground)
      sf.setOutsideBoundaryCondition({'FFactor'=>'GroundFCfactorMethod','LayeredGround'=>'Ground','Kiva'=>'Foundation'}.fetch(method['model']))
      if kiva
        sf.setAdjacentFoundation(kiva);sf.createSurfacePropertyExposedFoundationPerimeter('TotalExposedPerimeter',40.0)
      end
    elsif type=='Wall' && (item['walled_kiva'] || method['model']=='CFactor')
      rule=item.fetch('wall_rule',ground_rule);sf.setConstruction(construction(model,d,rule['assembly_id']))
      sf.setOutsideBoundaryCondition(kiva ? 'Foundation' : 'GroundFCfactorMethod');sf.setAdjacentFoundation(kiva) if kiva
    end
  end
  day=OpenStudio::Model::DesignDay.new(model);day.setName('Explicit synthetic input smoke')
  day.setMonth(7);day.setDayOfMonth(21);day.setDayType('SummerDesignDay');day.setMaximumDryBulbTemperature(32);day.setDailyDryBulbTemperatureRange(10)
  day.setBarometricPressure(101325*(1-2.25577e-5*site['elevation_m'])**5.2559)
  model.getSimulationControl.setRunSimulationforSizingPeriods(true);model.getSimulationControl.setRunSimulationforWeatherFileRunPeriods(false)
  model.getTimestep.setNumberOfTimestepsPerHour(4)
  variable=OpenStudio::Model::OutputVariable.new('Surface Inside Face Conduction Heat Transfer Rate',model);variable.setReportingFrequency('Hourly')
  dir=File.join(output,item.fetch('label'));FileUtils.mkdir_p(dir)
  ft=OpenStudio::EnergyPlus::ForwardTranslator.new;idf=ft.translateModel(model)
  raise ft.errors.map(&:logMessage).join('; ') unless ft.errors.empty?
  idf.save(OpenStudio::Path.new(File.join(dir,'source-25.1.idf')),true)
  # This minimal, audited object subset uses the target 26.2 IDD field layout.
  text=File.read(File.join(dir,'source-25.1.idf')).sub(/Version,\s*25\.1\s*;/m,'Version,26.2;')
  File.write(File.join(dir,'in.idf'),text)
  puts 'Prepared native input smoke: '+item['label']
end
