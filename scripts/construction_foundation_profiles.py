"""Internal source exposures and native interface profiles; no consumer geometry."""
import copy
import math
from collections import Counter


def footprint_boundary_length(polygons,tolerance=1e-6):
    """Cancel split shared edges in coplanar reference floor polygons.

    This is an outline length, not automatically the F-factor air-exposed
    perimeter. Kiva source rectangles must not be unioned as physical plans.
    """
    points=[tuple(p) for poly in polygons for p in poly]
    segments=[(tuple(p),tuple(poly[(i+1)%len(poly)])) for poly in polygons for i,p in enumerate(poly)]
    counts=Counter()
    for a,b in segments:
        vector=tuple(y-x for x,y in zip(a,b));length2=sum(v*v for v in vector)
        if length2<tolerance**2:raise ValueError('Degenerate source footprint edge')
        ts=[0.,1.]
        for p in points:
            t=sum((x-y)*v for x,y,v in zip(p,a,vector))/length2
            if tolerance<t<1-tolerance and sum((x-y-t*v)**2 for x,y,v in zip(p,a,vector))<=tolerance**2:
                ts.append(t)
        ts=sorted(set(round(t,12) for t in ts))
        for lo,hi in zip(ts,ts[1:]):
            ends=[tuple(round(x+t*v,6) for x,v in zip(a,vector)) for t in (lo,hi)]
            counts[tuple(sorted(ends))]+=1
    if any(n>2 for n in counts.values()):raise ValueError('Overlapping source footprint faces')
    return sum(math.dist(a,b) for (a,b),n in counts.items() if n==1)


def build_foundation_profile(source_reference:dict)->dict:
    if source_reference.get('status')!='recovered':raise ValueError('Unresolved source foundation physics')
    row=source_reference
    residential='record_id' in row
    original={s['id'] for c in row.get('captures',[]) for s in c['surfaces']}
    attrs={e['attributes']['id']:e['attributes'] for e in row.get('source_elements',[])}
    kiva={k['id']:copy.deepcopy(k) for k in row.get('kiva',[])}
    faces=[]
    for face in row['surfaces']:
        if residential and face['name'] not in original:continue
        f=copy.deepcopy(face)
        role={'Slab':'GroundFloor','FoundationWall':'FoundationWall','Floor':'FloorOverFoundation','RimJoist':'RimJoist'}.get(f.get('source_role')) if residential else {'Floor':'GroundFloor','Wall':'FoundationWall'}.get(f['surface_type'])
        if role is None:raise ValueError('Unknown source foundation interface role')
        matches=[k for k in attrs if f['name']==k or f['name'].startswith(k+' ') or f['name'].startswith(k+'_')]
        attr=attrs[max(matches,key=len)] if matches else {}
        fid=f.get('foundation_id')
        host=kiva[fid]['initialization']['host'] if fid else attr.get('interior_adjacent_to','assigned_bem_zone')
        f.update(role=role,thermal_host=host,source_attributes=copy.deepcopy(attr),
                 foundation_id=fid,source_element_id=max(matches,key=len) if matches else f['name'])
        if residential and not attr:raise ValueError('Unresolved HPXML foundation source identity: '+f['name'])
        if not isinstance(f['area_m2'],(int,float)) or f['area_m2']<=0:raise ValueError('Missing source interface area')
        faces.append(f)
    outline={'status':'not_physical_plan','reason':'Residential Kiva rectangles are solver reference geometry, not a building footprint'}
    if not residential:
        planes={}
        for f in faces:
            if f['role']=='GroundFloor':planes.setdefault(round(f['vertices'][0][2],5),[]).append(f['vertices'])
        try:outline={'status':'reference_outline_recovered','boundary_length_by_elevation_m':{str(z):footprint_boundary_length(polys) for z,polys in planes.items()},
                     'interpretation_note':'Outline length is not automatically direct-air F-factor exposed perimeter'}
        except ValueError as exc:outline={'status':'source_outline_unresolved','reason':str(exc),'interpretation_note':'Audit-only; no perimeter imputed or used to homogenize a native recipe'}
    return {'kind':'internal_foundation_profile','faces':faces,'kiva':kiva,'reference_outline':outline,
        'kiva_settings':copy.deepcopy(row.get('kiva_settings')),
        'host_airflow':copy.deepcopy(row.get('host_airflow')),
        'source_foundations':copy.deepcopy(row.get('source_foundations',[])),
        'source_only':True,'mass_policy':'foundation_interfaces_excluded_from_existing_interior_restoration'}
