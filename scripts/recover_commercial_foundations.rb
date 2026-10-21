# frozen_string_literal: true
# Native construction phases only: no loads, HVAC, annual schedules or simulation.
require 'json'
source, input, output = ARGV
require File.join(File.expand_path(source), 'lib/openstudio-standards')
OpenStudio::Logger.instance.standardOutLogger.setLogLevel(OpenStudio::Fatal)

def atlas_value(v)
  return v.get if v.respond_to?(:is_initialized) && v.is_initialized
  return nil if v.respond_to?(:is_initialized)
  v
end

def atlas_material(m)
  if m.to_StandardOpaqueMaterial.is_initialized
    x=m.to_StandardOpaqueMaterial.get
    return {name:m.nameString, model:'StandardOpaqueMaterial', roughness:x.roughness,
      thickness_m:x.thickness, conductivity_W_m_K:x.conductivity, density_kg_m3:x.density,
      specific_heat_J_kg_K:x.specificHeat, thermal_absorptance:x.thermalAbsorptance,
      solar_absorptance:x.solarAbsorptance, visible_absorptance:x.visibleAbsorptance}
  end
  x=m.to_OpaqueMaterial.get
  {name:m.nameString, model:m.to_MasslessOpaqueMaterial.is_initialized ? 'MasslessOpaqueMaterial' : 'AirGap',
   resistance_m2_K_W:x.thermalResistance,
   roughness:m.to_MasslessOpaqueMaterial.is_initialized ? m.to_MasslessOpaqueMaterial.get.roughness : nil,
   thermal_absorptance:x.thermalAbsorptance, solar_absorptance:x.solarAbsorptance,
   visible_absorptance:x.visibleAbsorptance}
end

def atlas_construction(c)
  if c.to_FFactorGroundFloorConstruction.is_initialized
    x=c.to_FFactorGroundFloorConstruction.get
    return {model:'FFactorGroundFloorConstruction', f_W_m_K:x.fFactor,
      reference_area_m2:x.area, reference_exposed_perimeter_m:x.perimeterExposed}
  elsif c.to_CFactorUndergroundWallConstruction.is_initialized
    x=c.to_CFactorUndergroundWallConstruction.get
    return {model:'CFactorUndergroundWallConstruction', c_W_m2_K:x.cFactor, reference_height_m:x.height}
  end
  x=c.to_Construction.get
  {model:'Construction', layers:x.layers.map { |m| atlas_material(m) }}
end

def atlas_ground_phases(std,model,building,cz,queries)
  file,line=std.method(:model_add_constructions).source_location
  text=File.readlines(file)[(line-1)..].join
  boundary=text.index('    # Make the default construction set for the building')
  raise 'Unrecognized pinned construction phase boundary' if boundary.nil?
  body=text[0...boundary].sub('def model_add_constructions','def atlas_native_ground_prefix')+"\n    return true\n  end\n"
  std.singleton_class.class_eval(body,file,line)
  std.atlas_native_ground_prefix(model,building,cz)
  climate_set=std.model_find_climate_zone_set(model,cz)
  queries.each_with_index do |q,i|
    next if q['context']=='compatibility_lookup'
    criteria={'template'=>std.template,'climate_zone_set'=>climate_set,
      'building_type'=>q['building_type'],'space_type'=>q['space_type'],'is_residential'=>q['is_residential']}
    data=std.model_find_object(std.standards_data['construction_sets'],criteria)
    data ||= std.model_find_object(std.standards_data['construction_sets'],criteria.reject { |k,_| k=='is_residential' })
    next if data.nil?
    set=OpenStudio::Model::DefaultConstructionSet.new(model)
    set.setName("atlas-ground-source-#{i}")
    ground=OpenStudio::Model::DefaultSurfaceConstructions.new(model)
    set.setDefaultGroundContactSurfaceConstructions(ground)
    {'floor'=>['GroundContactFloor','setFloorConstruction'],'wall'=>['GroundContactWall','setWallConstruction']}.each do |role,(type,setter)|
      construction_type=data["ground_contact_#{role}_standards_construction_type"]
      category=data["ground_contact_#{role}_building_category"]
      next if construction_type.nil? || category.nil?
      ground.send(setter,std.model_find_and_add_construction(model,climate_set,type,construction_type,category))
    end
    case q['context']
    when 'building_default'
      model.getBuilding.setDefaultConstructionSet(set)
    when 'space_type'
      model.getSpaceTypes.each do |st|
        name=st.standardsSpaceType.is_initialized ? st.standardsSpaceType.get : nil
        bt=st.standardsBuildingType.is_initialized ? st.standardsBuildingType.get : nil
        bt='' if name=='Attic'
        st.setDefaultConstructionSet(set) if name==q['space_type'] && bt==q['building_type']
      end
    when 'story_override'
      # Recovered source story classification and physical story membership.
      model.getBuildingStorys.each { |story| story.spaces.each { |s| s.setDefaultConstructionSet(set) } if story.nameString==q['story'] }
    else
      raise 'Unrecognized source construction scope'
    end
  end
  true
end

results=[]
standards={}
JSON.parse(File.read(input)).each do |r|
  begin
    template, building, climate=r.values_at('template','building_type','climate_zone')
    std=standards[template+'_'+building] ||= Standard.build(template+'_'+building)
    if r['recovery_mode']=='query_inventory'
      model=OpenStudio::Model::Model.new
      cz='ASHRAE 169-2013-'+climate
      lookup=std.model_get_lookup_name(building)
      base=std.model_get_construction_set(lookup)
      physics={}
      if !base.nil?
        physics['explicit_floor']=std.model_get_construction_properties(model,'GroundContactFloor','Unheated',base['ground_contact_floor_building_category'],cz)
        physics['explicit_wall']=std.model_get_construction_properties(model,'GroundContactWall','Mass',base['exterior_wall_building_category'],cz)
      end
      cs=std.model_find_climate_zone_set(model,cz)
      physics['defaults']=r.fetch('source_queries').filter_map do |q|
        next if q['context']=='compatibility_lookup'
        crit={'template'=>template,'climate_zone_set'=>cs,'building_type'=>q['building_type'],'space_type'=>q['space_type'],'is_residential'=>q['is_residential']}
        data=std.model_find_object(std.standards_data['construction_sets'],crit)
        data ||= std.model_find_object(std.standards_data['construction_sets'],crit.reject { |k,_| k=='is_residential' })
        next if data.nil?
        ['floor','wall'].to_h do |role|
          typ=data["ground_contact_#{role}_standards_construction_type"]
          cat=data["ground_contact_#{role}_building_category"]
          [role,typ.nil? || cat.nil? ? nil : std.model_get_construction_properties(model,role=='floor' ? 'GroundContactFloor' : 'GroundContactWall',typ,cat,cz)]
        end.merge('scope'=>q)
      end
      # Deduplicate only equal physical lookup results, never unequal climate rules.
      strip=lambda do |v|
        case v
        when Hash then v.reject { |k,_| ['climate_zone_set','template','notes'].include?(k) }.transform_values { |x| strip.call(x) }
        when Array then v.map { |x| strip.call(x) }
        else v
        end
      end
      f,l=std.method(:model_custom_geometry_tweaks).source_location
      lines=File.readlines(f)[(l-1)..]
      finish=lines[1..].index { |line| line.match?(/^  def /) }
      method_lines=finish.nil? ? lines : lines[0..finish]
      # A forwarded or used climate argument conservatively prevents sharing.
      climate_sensitive=method_lines.drop(1).any? { |line| !line.lstrip.start_with?('#') && line.include?('climate_zone') }
      signature=strip.call(physics)
      signature['geometry_climate_context']=climate if climate_sensitive
      results << r.reject { |k,_| k=='source_queries' }.merge(status:'source_queries_recovered',physics_signature:signature,
        geometry_climate_sensitive:climate_sensitive,geometry_caller:[f,l])
      File.write(output,JSON.pretty_generate({runtime_version:OpenStudio.openStudioVersion,results:results})+"\n") if (results.size % 50).zero?
      next
    end
    model=std.send(:load_geometry_osm, std.geometry_file)
    model.getBuilding.setStandardsBuildingType(building)
    cz='ASHRAE 169-2013-'+climate
    raise 'Source geometry tweak failed' unless std.model_custom_geometry_tweaks(model,building,cz,std.prototype_input)
    before=model.getSurfaces.to_h { |s| [s.nameString,s.outsideBoundaryCondition] }
    success=if r['recovery_mode']=='ground_phases'
      atlas_ground_phases(std,model,building,cz,r.fetch('source_queries'))
    else
      std.model_add_constructions(model,building,cz)
    end
    raise 'Source construction phase failed' unless success
    faces=model.getSurfaces.sort_by(&:nameString).filter_map do |s|
      next unless ['Ground','GroundFCfactorMethod','OtherSideCoefficients','Foundation'].include?(before[s.nameString]) ||
        ['Ground','GroundFCfactorMethod','OtherSideCoefficients','Foundation'].include?(s.outsideBoundaryCondition)
      raise 'Unassigned source ground surface: '+s.nameString unless s.construction.is_initialized
      space=s.space.get
      st=space.spaceType.is_initialized ? space.spaceType.get : nil
      {name:s.nameString, surface_type:s.surfaceType, boundary_before:before[s.nameString],
       boundary:s.outsideBoundaryCondition, area_m2:s.grossArea,
       vertices:s.vertices.map { |v| p=space.transformation*v; [p.x,p.y,p.z] },
       space:space.nameString,
       space_type:st && st.standardsSpaceType.is_initialized ? st.standardsSpaceType.get : nil,
       construction:atlas_construction(s.construction.get),
       explicit:!s.isConstructionDefaulted}
    end
    defaults=model.getDefaultConstructionSets.sort_by(&:nameString).filter_map do |set|
      next unless set.defaultGroundContactSurfaceConstructions.is_initialized
      g=set.defaultGroundContactSurfaceConstructions.get
      {name:set.nameString, floor:g.floorConstruction.is_initialized ? atlas_construction(g.floorConstruction.get) : nil,
       wall:g.wallConstruction.is_initialized ? atlas_construction(g.wallConstruction.get) : nil}
    end
    results << r.reject { |k,_| k=='source_queries' }.merge(status:'recovered',surfaces:faces,defaults:defaults,
      geometry_file:'data/'+std.geometry_file,
      caller:std.method(:model_add_constructions).source_location)
  rescue StandardError => e
    results << r.merge(status:'blocked',error:e.message,trace:e.backtrace.first(6))
  end
  File.write(output,JSON.pretty_generate({runtime_version:OpenStudio.openStudioVersion,results:results})+"\n")
end
File.write(output,JSON.pretty_generate({runtime_version:OpenStudio.openStudioVersion,results:results})+"\n")
puts "Captured #{results.size} source commercial foundation contexts"
