"""Presentation for the optional complete water-reporting release."""
from pathlib import Path
import shutil
import zipfile

from scripts.common import stable_id


def service_page(path_id):
    return 'water-reporting/services/'+stable_id('water_service',path_id)+'.md'


def program_html(current, row, packet):
    from scripts.site import anchor, display_value
    services={s['path_id']:s for s in packet['services']}
    page='## Complete water reporting variant v'+packet['release_version']+'\n\n'
    page+='**'+display_value(row['reporting_status'])+'**. Local source state: **'+display_value(row['local_draw_status'])+'**.\n\n'
    page+='The attributed mixed-draw curve is a reporting equivalent. Its reference peak is not a downstream load magnitude. Reporting weights do not place physical fixtures or heat/moisture gains in this program.\n\n'
    if not row['components']:
        page+='The plotted zero means **no draw attributed to this program under this reporting policy**. An unknown local source assignment remains unknown; shared demand is accounted for separately below.\n\n'
    for c in row['components']:
        s=services[c['path_id']]
        page+=anchor(current,service_page(s['path_id']),s['end_use']+' / '+s['source_schedule_name'])+' · '+display_value(s['allocation_status'])+' · reporting share '+display_value(c['allocation_weight'])+'\n\n'
    shared=[services[k] for k in row['building_service_path_ids'] if services[k]['allocation_status']=='retained_shared_service']
    if shared:
        page+='### Shared building services retained separately\n\nThese curves are applied once per building, not once per linked program. No allocation or physical location is inferred.\n\n'
        for s in shared:
            page+=anchor(current,service_page(s['path_id']),s['end_use']+' / '+s['source_schedule_name'])+'\n\n'
    page+=anchor(current,'water-reporting/index.md','Reporting policy, complete service catalogue and checksums')+' · '+anchor(current,'guides/hot-water.md','Source and derived allocation methods')+'\n\n'
    return page


def generate(root, packet, path, data, pilot=False):
    from scripts.site import anchor, display_value, explorer_html, friendly, page_header, write_site_json, write_text
    from scripts.catalogue_names import program_title
    root=Path(root);path=Path(path);version='v'+packet['release_version']
    destination=root/'water-reporting'/version;destination.mkdir(parents=True)
    with zipfile.ZipFile(destination/'snapshot.zip','w',compression=zipfile.ZIP_STORED) as archive:
        for src in sorted(path.rglob('*'),key=lambda p:p.relative_to(path).as_posix()):
            if not src.is_file():continue
            name=src.relative_to(path).as_posix()
            info=zipfile.ZipInfo(name,date_time=(2026,10,5,0,0,0));info.create_system=3
            info.compress_type=zipfile.ZIP_STORED;info.external_attr=0o644<<16
            archive.writestr(info,src.read_bytes())
            if src.name in {'manifest.json','water-reporting.json','LICENSE'}:
                shutil.copyfile(src,destination/src.name)
    programs={p['id']:p for p in data['programs']}
    for shape in packet['schedules']:
        sid=shape['id'];current='releases/v0.2.0/schedules/'+sid+'.md'
        write_site_json(root/f'releases/v0.2.0/records/{sid}.json',{'record':shape})
        page=page_header(shape['source_name'],'v0.2.0',sid,False)
        page+='Optional water reporting '+version+'. This is an explicitly derived attributed-volume shape, with no water-heater energy or temperature-feedback inference. Original source rules remain in the bound completion release.\n\n'
        page+=explorer_html(current,'v0.2.0',{'attributed_mixed_draw':sid})+'\n\n'
        page+=display_value(shape)+'\n\n'+anchor(current,'water-reporting/index.md','Reporting scope and source services')+'\n'
        write_text(root,current,page)
    index='# Complete water reporting catalogue\n\n'
    index+='Optional deterministic reporting variant **'+version+'** covers **734 active programs**. **279 source-only program allocations remain unknown** in the original release; the reporting variant supplies curves, explicit reporting zeros and shared-service references for all active programs. This is operational schedule coverage, not full simulation readiness or 100% source-measured allocation.\n\n'
    index+='Apply each original fixture component once: either its program allocations, or the retained shared service. Never add both. Design-occupant weights use deduplicated benchmark floor areas and multipliers; they do not change geometry-atlas areas. Component temperatures remain separate.\n\n'
    index+=display_value(packet['summary'])+'\n\n'
    for name,label in [('water-reporting.json','Canonical program/service tables and evidence'),('snapshot.zip','Complete reproducible snapshot'),('manifest.json','Manifest and SHA-256 checksums')]:
        index+=anchor('water-reporting/index.md',f'water-reporting/{version}/{name}',label)+'\n\n'
    index+='<div class="atlas-table"><table><thead><tr><th>Building</th><th>Template</th><th>Service</th><th>Allocation basis</th><th>Reporting beneficiaries</th></tr></thead><tbody>'
    for s in packet['services']:
        selected=not pilot or (s['building_type'],s['template'])==('MediumOffice','90.1-2013')
        if not selected:continue
        current=service_page(s['path_id'])
        label=friendly(s['building_type'])+' / '+s['end_use']+' · '+s['template']
        page=page_header(label,version,s['path_id'],False)
        page+='Reporting allocation: **'+display_value(s['allocation_status'])+'**. Source allocation: **'+display_value(s['source_allocation_status'])+'**.\n\n'
        page+='This service retains its original draw timing and target temperature. Derived beneficiaries do not establish physical fixture location or zone gains. Retained shared services remain a separate building demand.\n\n'
        if s['allocation_weights']:
            page+='## Reporting shares\n\n'
            for pid,weight in s['allocation_weights'].items():
                p=programs[pid]
                page+=anchor(current,f'releases/v0.2.0/programs/{pid}.md',program_title(p))+' · '+display_value(weight)+'\n\n'
        else:
            page+='**Shared service:** apply once per building; program beneficiaries remain unspecified.\n\n'
        page+=explorer_html(current,'v0.2.0',{'source_mixed_draw':s['source_schedule_id'],
                                              'conserved_peak_normalized_draw':s['equivalent_schedule_id']})+'\n\n'
        page+='## Source conditions and reporting interpretation\n\n'+display_value(s)+'\n\n'
        page+=anchor(current,'commercial-completion/paths/'+stable_id('fixture_path',s['path_id'])+'.md','Exact source path and field evidence')+' · '+anchor(current,'water-reporting/index.md','Complete reporting catalogue')+'\n'
        write_text(root,current,page)
        names=[program_title(programs[pid]) for pid in s['allocation_weights']]
        index+='<tr>'+''.join('<td>'+v+'</td>' for v in [display_value(friendly(s['building_type'])),display_value(s['template']),anchor('water-reporting/index.md',current,s['end_use']),display_value(s['allocation_status']),display_value(names or 'Shared building service')])+'</tr>'
    index+='</tbody></table></div>\n'
    write_text(root,'water-reporting/index.md',index)
