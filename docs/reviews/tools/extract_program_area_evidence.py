"""Inspection wrapper over the production represented-area extractor."""
import math
from scripts.common import ROOT, load_atlas, dump_json
from scripts.definition_contract import BuildContext
from scripts.program_composition import extract_areas


def main():
    atlas=load_atlas(ROOT/'data/releases/v0.2.0')
    context=BuildContext(root=ROOT,scope='full',atlas=atlas)
    sources={s['id']:s for s in atlas['source_files']}
    output=[]
    for (family,template),areas in extract_areas(context).items():
        denominator=math.fsum(a['represented_area_m2'] for a in areas)
        source=sources[areas[0]['source_file_id']]
        rows=[{'program_id':a['program_id'],'source_building_type':a['source_building_type'],
               'source_space_type':a['source_space_type'],
               'share_percent':100*a['represented_area_m2']/denominator if a['area_status']=='derived' else None,
               'area_status':'derived' if a['area_status']=='derived' else 'not_counted',
               'represented_counted_area_m2':a['represented_area_m2'],
               'counted_space_handles':a['space_handles'],
               'uncounted_space_handles':a['uncounted_space_handles']} for a in sorted(areas,key=lambda r:r['source_space_type'])]
        output.append({'building_type':family,'template':template,
                       'source_family':next(p['source_family'] for p in atlas['programs'] if p['id']==areas[0]['program_id']),
                       'geometry':source['path'],'sha256':source['sha256'],'source_revision':source['version'],
                       'denominator_m2':denominator,'rows':rows})
    dump_json(ROOT/'build/reviews/program-area-evidence.json',output)
    print('Verified',len(output),'contexts and',sum(len(m['rows']) for m in output),'source programs')


if __name__=='__main__':main()
