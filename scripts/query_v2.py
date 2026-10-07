"""Static selective definition delivery v2; v1 transport and URLs remain intact."""
import argparse
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
from jsonschema import Draft202012Validator, ValidationError
from scripts.common import ROOT, load_json
from scripts.definition_contract import PRIMARY, TABLES, canonical, stable_id
from scripts.query_delivery import descriptor, safe_path, checked_target, MAX_PACKET_BYTES
from scripts.query_client import QueryClient as TransportClient, QueryError, same_scalar

VERSION='2.0.0'
FILTERS={'id','building_type','template','source_family','climate','detail','system_type',
         'representation','role','gate','derivation'}
GROUPS=('building_type','template','source_family','evidence_view')
LAZY_FIELDS={'air_exchange','source_set','source_descriptor'}


def generate_delivery(bundle,target):
    target=checked_target(target);target.mkdir(parents=True,exist_ok=True)
    def write(value,compressed=True):
        decoded=canonical(value)
        content=gzip.compress(decoded,mtime=0) if compressed else decoded
        if compressed:
            content=content[:9]+b'\xff'+content[10:]
        href='resources/'+hashlib.sha256(content).hexdigest()+('.json.gz' if compressed else '.json')
        path=target/href;path.parent.mkdir(exist_ok=True)
        if path.exists() and path.read_bytes()!=content:raise ValueError('Immutable resource collision')
        path.write_bytes(content);ref=descriptor(href,content)
        if compressed:ref.update(encoding='gzip',decoded_size_bytes=len(decoded))
        return ref
    supporting={}
    for table in TABLES:
        if table in PRIMARY.values():continue
        refs={}
        for row in bundle.get(table,[]):
            refs[row['id']]=write({'schema_version':VERSION,'kind':'resource','table':table,'record':row})
        supporting[table]=write({'schema_version':VERSION,'kind':'resource_index','table':table,'resources':refs})
    types={}
    details={}
    for kind,table in PRIMARY.items():
        groups={};fields=set()
        for original in sorted(bundle.get(table,[]),key=lambda r:r['id']):
            row=copy.deepcopy(original)
            for key in LAZY_FIELDS & row.keys():
                rid=stable_id('detail',{'id':row['id'],'field':key})
                ref=write({'schema_version':VERSION,'kind':'resource','table':'details',
                           'record':{'id':rid,'field':key,'value':row[key]}})
                details[rid]=ref;row[key]={'resource_id':rid,'resource':ref}
            fields.update(row)
            group=tuple(row.get(k) for k in GROUPS)
            groups.setdefault(group,[]).append(row)
        routes=[]
        for group,rows in sorted(groups.items(),key=lambda item:str(item[0])):
            packets=[];chunk=[]
            def packet(values):return {'schema_version':VERSION,'kind':'packet','record_type':kind,'records':values}
            for row in rows:
                if len(canonical(packet(chunk+[row])))>MAX_PACKET_BYTES:
                    if not chunk:raise ValueError('Definition exceeds selective packet bound: '+row['id'])
                    packets.append(write(packet(chunk)));chunk=[]
                if len(canonical(packet([row])))>MAX_PACKET_BYTES:raise ValueError('Oversized definition: '+row['id'])
                chunk.append(row)
            if chunk:packets.append(write(packet(chunk)))
            routes.append({'selectors':dict(zip(GROUPS,group)),'record_ids':[r['id'] for r in rows], 'packets':packets})
        index=write({'schema_version':VERSION,'kind':'index','record_type':kind,'routes':routes})
        types[kind]={'index':index,'fields':sorted(fields),'filter_fields':sorted(FILTERS & fields),
                     'record_count':len(bundle.get(table,[]))}
    supporting['details']=write({'schema_version':VERSION,'kind':'resource_index','table':'details','resources':details})
    schema=write({'schema_version':VERSION,'kind':'resource','record':load_json(ROOT/'schemas/query-v2.schema.json')})
    manifest={'schema_version':VERSION,'kind':'manifest','definition_schema_version':'1.0.0',
              'max_packet_bytes':MAX_PACKET_BYTES,'record_types':types,'supporting_tables':supporting,
              'schema':schema,'dependencies':bundle.get('dependencies',{}),
              'interpretation':'Fixed library definitions; null and required consumer inputs stay explicit.'}
    manifest['snapshot_id']=hashlib.sha256(canonical(manifest)).hexdigest()
    content=canonical(manifest);href='snapshots/'+manifest['snapshot_id']+'/manifest.json'
    path=target/href;path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=content:raise ValueError('Immutable snapshot collision')
    path.write_bytes(content)
    latest={'schema_version':VERSION,'kind':'latest','snapshot_id':manifest['snapshot_id'],
            'manifest':descriptor(href,content)}
    (target/'latest.json').write_bytes(canonical(latest))
    return manifest


class QueryClient(TransportClient):
    """Reuse checksum, path, HTTP-origin, strict JSON and decompression protection."""
    def _artifact(self,value,expected_kind=None):
        if not isinstance(value,dict) or value.get('schema_version')!=VERSION:
            raise QueryError('unsupported_schema','Expected delivery schema 2.0.0')
        try:Draft202012Validator(load_json(ROOT/'schemas/query-v2.schema.json')).validate(value)
        except ValidationError as error:raise QueryError('invalid_artifact',error.message) from error
        if expected_kind and value['kind']!=expected_kind:
            raise QueryError('invalid_artifact','Unexpected artifact kind')
        if value['kind']=='packet' and len(canonical(value))>MAX_PACKET_BYTES:
            raise QueryError('invalid_artifact','Packet exceeds bound')

    def query(self,kind,filters,fields,view='source'):
        if kind not in PRIMARY or view not in {'source','reviewed'}:
            raise QueryError('invalid_request','Unknown primary kind or evidence view')
        info=self.manifest['record_types'][kind]
        if (not isinstance(filters,dict) or set(filters)-set(info['filter_fields']) or
                any(isinstance(v,(dict,list)) or isinstance(v,float) and not math.isfinite(v) for v in filters.values()) or
                not isinstance(fields,list) or not fields or any(not isinstance(f,str) for f in fields) or
                len(fields)!=len(set(fields)) or set(fields)-set(info['fields'])):
            raise QueryError('invalid_request','Unknown/non-scalar filter or invalid projected field')
        index=self.fetch(info['index']);rows=[]
        for route in index['routes']:
            if view=='source' and route['selectors']['evidence_view']!='source':continue
            if any(key in route['selectors'] and not same_scalar(route['selectors'][key],val)
                   for key,val in filters.items()):continue
            if 'id' in filters and filters['id'] not in route['record_ids']:continue
            for ref in route['packets']:rows.extend(self.fetch(ref)['records'])
        if view=='reviewed':
            replaced={r['source_definition_id'] for r in rows if r.get('source_definition_id')}
            rows=[r for r in rows if r['id'] not in replaced]
        result=[]
        for row in rows:
            if all(val in row.get('gate',[]) if key=='gate' else
                   val in row.get('available_details',[row.get('detail')]) if key=='detail' else same_scalar(row.get(key),val)
                   for key,val in filters.items()):
                result.append({'id':row['id'],'fields':{key:row.get(key) for key in fields},
                               'evidence_view':row['evidence_view'],'derivation':row['derivation']})
        return {'schema_version':VERSION,'kind':'response','snapshot_id':self.manifest['snapshot_id'],
                'manifest':self.manifest_ref,'record_type':kind,'requested_view':view,
                'match_count':len(result),'records':sorted(result,key=lambda r:r['id'])}

    def resource(self,resource_id):
        if not isinstance(resource_id,str) or not resource_id:
            raise QueryError('invalid_request','Resource ID required')
        for table,ref in self.manifest['supporting_tables'].items():
            index=self.fetch(ref)
            if resource_id in index['resources']:
                return self.fetch(index['resources'][resource_id])
        raise QueryError('not_found','Unknown supporting resource ID')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    from scripts.definition_release import read_bundle
    result=generate_delivery(read_bundle(args.input),args.output)
    print('Generated v2 snapshot '+result['snapshot_id'])


if __name__=='__main__':main()
