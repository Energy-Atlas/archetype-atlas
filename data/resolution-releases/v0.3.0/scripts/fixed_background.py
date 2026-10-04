"""Extract fixed residential refrigeration shapes from the pinned default table.

This is a finite table export, not a parametric occupant/activity generator.
"""
import argparse
import csv
import datetime as dt
import math
from scripts.common import ROOT, dump_json, load_json
from scripts.fetch import verify_file


SOURCE_PATH='resources/hpxml-measures/HPXMLtoOpenStudio/resources/data/default_schedules.csv'
ELEMENTS={'WeekdayScheduleFractions':('weekday_fractions',24),
          'WeekendScheduleFractions':('weekend_fractions',24),
          'MonthlyScheduleMultipliers':('monthly_multipliers',12)}


def build(cache_root=ROOT/'data/raw',evidence_lock=ROOT/'sources/schedule-evidence-lock.json'):
    lock=load_json(evidence_lock)
    entry=next(e for e in lock['files'] if e['source_id']=='resstock' and e['path']==SOURCE_PATH)
    source=verify_file(entry,cache_root)
    schedules={}
    with source.open(encoding='utf-8',newline='') as stream:
        for number,row in enumerate(csv.DictReader(stream),2):
            name,element=row['Schedule Name'],row['Element']
            if name not in {'refrigerator','freezer'} or element not in ELEMENTS:
                continue
            field,length=ELEMENTS[element]
            values=[float(v.strip()) for v in row['Values'].split(',')]
            if len(values)!=length or any(not math.isfinite(v) or v<0 for v in values):
                raise ValueError('Invalid fixed schedule source shape')
            schedule=schedules.setdefault(name,{'id':name,'unit':'dimensionless','temperature_dependent':False,
                'interval_convention':'Local standard time; hour 0 covers [00:00,01:00); Monday-Friday weekday, Saturday-Sunday weekend; January-December multipliers',
                'special_days':'No source holiday/design-day override reported for this fixed variant',
                'normalization':'weekday/weekend hourly fraction multiplied by month multiplier, divided by the maximum possible product; load magnitude excluded',
                'evidence':[]})
            if field in schedule:
                raise ValueError('Duplicate fixed source element')
            schedule[field]=values
            schedule['evidence'].append({'source_locator':entry['url']+'#row='+str(number)+'/'+element,
                'source_revision':entry['source_revision'],'source_file_sha256':entry['sha256'],
                'original_field':element,'original_value':row['Values'],'original_unit':'dimensionless',
                'transformation':'Parse comma-separated values in source order; preserve hourly fractions and monthly multipliers; peak normalization only at evaluation',
                'extraction_date':lock['retrieval_date'],'interpretation_note':'User-selected fixed default variant; no runtime temperature coefficients or weather input; '+row['Data Source']})
    for schedule in schedules.values():
        if not all(field in schedule for field,_ in ELEMENTS.values()):
            raise ValueError('Incomplete refrigeration defaults')
        schedule['peak_divisor']=max(schedule['weekday_fractions']+schedule['weekend_fractions'])*max(schedule['monthly_multipliers'])
        if schedule['peak_divisor']<=0:
            raise ValueError('Nonpositive fixed shape peak')
    if set(schedules)!={'refrigerator','freezer'}:
        raise ValueError('Missing refrigeration defaults')
    return {'schema_version':'0.1.0','variant':'fixed_source_default_no_temperature_feedback',
            'schedules':schedules}


def annual_series(schedule,year):
    start=dt.datetime(year,1,1); stop=dt.datetime(year+1,1,1)
    series=[]
    while start<stop:
        fractions=schedule['weekday_fractions'] if start.weekday()<5 else schedule['weekend_fractions']
        series.append(fractions[start.hour]*schedule['monthly_multipliers'][start.month-1]/schedule['peak_divisor'])
        start+=dt.timedelta(hours=1)
    return series


def annual_packet(packet,year=2007):
    return {'metadata':{'year':year,'timestep_minutes':60,
            'status':packet['variant'],'columns':{k:'dimensionless' for k in packet['schedules']}},
            'series':{k:annual_series(s,year) for k,s in packet['schedules'].items()}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=str,default='build/fixed-background-schedules.json')
    args=parser.parse_args()
    dump_json(args.target,build())


if __name__=='__main__':
    main()
