"""Bounded port of Standards 0.8.6 source profiles/formulas and ComStock BPR.

Only frozen Constant/Hourly rules and the inspected hours/tstat modes are
accepted. This is not a schedule-expression interpreter. Formula anchors,
out-of-order correction, minute truncation and export precision follow the
selected native methods, including their zero/full-day decisions.
"""
import copy
from datetime import date, timedelta
import math

from ..calendar import evaluate_rules
from ..errors import GeneratorError


def _error(path, message):
    raise GeneratorError('invalid_commercial_context', '/commercial/'+path, message)


def _number(value, path, minimum=0, maximum=math.inf):
    if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        _error(path, 'Finite number in source range required')
    return float(value)


def _round(value, places):
    # Ruby3.2.2 numeric.c:round_half_up/flo_round, selected source digit counts.
    # Decimal(str(value)) loses the native scaled-double tie boundary.
    if not math.isfinite(value) or places not in {0,2,5,6}:
        _error('rounding','Finite bounded selected native rounding operation required')
    scale=10.0**places
    scaled=value*scale
    integer=math.floor(scaled) if scaled>0 else math.ceil(scaled)
    rounded=integer+(scaled-integer>=.5) if scaled>0 else integer-(integer-scaled>=.5)
    if scale!=1:
        if value>0 and (rounded+.5)/scale<=value: rounded+=1
        elif value<=0 and (rounded-.5)/scale>=value: rounded-=1
    return float(rounded/scale)


def _stored(value):
    # Native OpenStudio ScheduleDay.addValue IDF double storage, independently
    # captured with positive/negative and occupancy multiplication probes.
    return float(format(value,'.15g'))


def _points(values):
    if len(values)==1:
        return [[24.0,float(values[0])]]
    return [[float(i+1),float(v)] for i,v in enumerate(values) if i==23 or v!=values[i+1]]


def _value(points, hour):
    return next((value for until,value in points if until >= hour),points[-1][1])


def _hourly(points, steps):
    # Source compares version strings lexically: native3.10.0 < '3.8.0'.
    # Its legacy getter samples at the smallest interval (at most15 minutes)
    # and rounds5. If that interval does not divide60 it omits the final tail.
    minutes=[int(round(time*60)) for time,_ in points]
    previous=0; interval=15
    for minute in minutes:
        interval=min(interval,minute-previous); previous=minute
    interval=int(_round(interval,0))
    if interval<=0: _error('hourly_getter','Native zero interval has undefined hourly getter')
    offsets=list(range(interval,61,interval))
    native_points=list(zip(minutes,[value for _,value in points]))
    # Native ScheduleDay.getValue samples its model-timestep timeSeries;
    # off-grid queries select the next timestep endpoint (No interpolation).
    query_offsets=[math.ceil(offset/(60/steps))*(60/steps) for offset in offsets]
    return [_round(math.fsum(next((value for until,value in native_points if until>=h*60+offset),native_points[-1][1])
                       for offset in query_offsets)/len(offsets),5) for h in range(24)]


def _hoo(points):
    start=next((time for time,value in points if value==0),None)
    end=next((time for time,value in points if value==1),None)
    if start is None: start=end
    if end is None: end=start
    if len(points)>3 or start is None or end is None:
        _error('occupancy_aggregation','Source inferred operating profile is invalid')
    hours=(24 if all(v==1 for _,v in points) else 0) if start==end else (end-start)%24
    return {'hoo_start':start,'hoo_end':end,'hoo_hours':hours}


def _close_gaps(points):
    # model_infer_hours_of_operation_building: keep largest vacancy gap.
    if len(points)<=3: return points
    latest=next((time for time,value in reversed(points) if value>0),None)
    if latest is None: return points
    wrap=24-latest if points[0][1]==0 and points[-1][1]==0 else 0
    first_zero=next(time for time,value in points if value==0)
    gaps={}; prev_time=0; prev_value=None
    for time,value in points:
        if time==0 or value==prev_value: continue
        if value==0: gaps[prev_time]=wrap+first_zero if time==24 else time-prev_time
        prev_time,prev_value=time,value
    gap_start=max(gaps,key=gaps.get); gap_end=gap_start+gaps[gap_start]
    if gap_end>24: gap_end-=24
    result={gap_start:1.0,gap_end:0.0,24.0:0.0 if gap_start>gap_end else 1.0}
    return [[time,value] for time,value in sorted(result.items())]


def _infer(context):
    aggregation=context['occupancy_aggregation']
    if not isinstance(aggregation,dict): _error('occupancy_aggregation','Explicit aggregation object required')
    if aggregation.get('policy')!='explicit_single_nonresidential_reference_carrier':
        _error('occupancy_aggregation/policy','Only audited explicit nonresidential reference carrier is supported')
    parts=aggregation.get('constituents')
    if not isinstance(parts,list) or len(parts)!=1:
        _error('occupancy_aggregation/constituents','Exact single-profile inference carrier required; mixed buildings need new validation')
    part=parts[0]
    if not isinstance(part,dict) or part.get('residential') is not False or not part.get('evidence'):
        _error('occupancy_aggregation/constituents','Explicit nonresidential classification and source evidence required')
    weight=_number(part.get('nominal_people'),'occupancy_aggregation/nominal_people')
    if weight==0: _error('occupancy_aggregation/nominal_people','Positive normalized inference weight required')
    raw=evaluate_rules(part.get('schedule'),context['year'],[])['values']
    profiles=[];groups={}
    for day in range(365):
        values=[_round(v*weight,6)/weight for v in raw[24*day:24*(day+1)]]
        threshold=min(values)+(max(values)-min(values))*.25
        binary=[1.0 if value!=0 and value>=threshold else 0.0 for value in values]
        points=_close_gaps(_points(binary)); operation=_hoo(points)
        weekday=(date(context['year'],1,1)+timedelta(days=day)).weekday()
        key=(min(weekday,5) if weekday<6 else 6,tuple(map(tuple,points)))
        # All weekdays are one source category; Saturdays and Sundays separate.
        key=(0 if weekday<5 else weekday, key[1])
        groups.setdefault(key,[]).append(day+1)
        profiles.append((key,operation,points))
    daily=[]
    for key,operation,points in profiles:
        daily.append(dict(operation,days_used=list(groups[key])))
    return {'daily_hoo':daily,'daily_profiles':[points for _,_,points in profiles],
            'source_weighted_occupancy_precision_decimals':6,
            'interpretation':'Declared inference carrier; no actual populated-building or arbitrary-scale equivalence claim'}


def _formula(points, original_hoo, floor, ceiling, mode):
    # schedule_ruleset_get_parametric_inputs, numeric representation of its
    # exact generated anchors; no source expression evaluation at runtime.
    values=[v for _,v in points]; raw={}
    for j,(time,value) in enumerate(points):
        if len(points)>1 and j==len(points)-1 and value==values[0]: continue
        next_value=values[j+1] if j+1<len(points) else values[0]
        if len(set(values))<3:
            raw[time]=[value,next_value]
        else:
            prev_time=points[j-1][0] if j>0 else points[-1][0]-24
            next_time=points[j+1][0] if j+1<len(points) else points[0][0]+24
            delta=min(2.0,(time-prev_time)*.5,(next_time-time)*.5)
            left=time-delta
            if left not in raw: raw[left+24 if left<0 else left]=[value]
            right=time+delta
            raw[right-24 if right>24 else right]=[next_value]
    result=[]; tstat_start_values=None
    for time,vals in sorted(raw.items()):
        starts=original_hoo['hoo_start']; ends=original_hoo['hoo_end']; mid=starts+original_hoo['hoo_hours']*.5
        deltas=[]
        for anchor in (starts,mid,ends):
            options=[anchor-time,anchor-time+24,anchor-time-24]
            deltas.append(min(options,key=abs))
        index=min(range(3),key=lambda i:abs(deltas[i])); delta=_round(deltas[index],2)
        converted=[]
        for val in vals:
            converted.append(('floor' if val==floor else 'ceiling' if val==ceiling else val) if len(set(values))<3 else val)
        if mode=='tstat':
            if index==0 and tstat_start_values is None:
                index=0; delta=0; tstat_start_values=list(converted)
            else:
                index=2; delta=0
                if tstat_start_values is not None: converted=list(reversed(tstat_start_values))
        result.append({'anchor':('start','mid','end')[index],'delta':delta,'values':converted})
    return result


def _apply(formula, start, end, floor, ceiling, frequency):
    # schedule_day_adjust_from_parameters including source mutation order.
    occupied=end-start if end>=start else 24+end-start
    mid=start+occupied*.5
    minute_options=[i*60*frequency for i in range(int(1/frequency)+1)]
    mid=math.floor(mid)+min(minute_options,key=lambda v:abs(v-(mid%1)*60))/60
    numbers={}
    for entry in formula:
        time={'start':start,'mid':mid,'end':end}[entry['anchor']]-entry['delta']
        numbers[time]=[floor if value=='floor' else ceiling if value=='ceiling' else value for value in entry['values']]
    pairs=[[time,value] for time,vals in numbers.items() for value in vals]
    negatives={}; min_times={}
    for i,pair in enumerate(pairs):
        if pair[0]<0: negatives[i]=pair[0]; pair[0]+=24
        min_times[i]=pair[0]
    rotation=min(min_times,key=min_times.get); pairs=pairs[rotation:]+pairs[:rotation]
    last=None
    for i,pair in enumerate(pairs):
        if last is None: last=pair[0]
        elif pair[0]<last or i in negatives:
            if i in negatives: updated=0.0
            else:
                buffer=pairs[i-1][0] if i<2 else pairs[i-1][0]-pairs[i-2][0]
                updated=pairs[i-1][0]-min(frequency,buffer)
            pairs[i-1][0]=updated; pair[0]=updated; last=updated
        else: last=pair[0]
    i=0
    while i<len(pairs):
        time,value=pairs[i]
        next_time,next_value=pairs[i+1] if i+1<len(pairs) else (pairs[0][0]+24,pairs[0][1])
        length=next_time-time
        if length>frequency and value!=next_value:
            interpolated=time+frequency
            new_value=next_value*(interpolated-time)/length+value*(next_time-interpolated)/length
            pairs.insert(i+1,[interpolated,new_value])
        i+=1
        if len(pairs)>2000: _error('formula','Source interpolation did not converge')
    seen=set(); unique=[]
    for pair in pairs:
        if pair[0] not in seen: unique.append(pair); seen.add(pair[0])
    rotation=0
    for pair in reversed(unique):
        if pair[0]>24: rotation-=1; pair[0]-=24
    if rotation: unique=unique[rotation:]+unique[:rotation]
    if int(unique[-1][0])!=24: unique.append([24.0,unique[0][1]])
    # Native ScheduleDay.addValue sorts times, overwrites identical truncated
    # minute times and ignores times outside its legal day interval.
    result={}
    for time,value in unique:
        hour=math.floor(time); minute=math.floor((time-hour)*60)
        native_time=(hour*60+minute)/60
        if 0<native_time<=24: result[native_time]=_stored(value)
    if not result: _error('formula','Source emitted no valid profile points')
    return [[time,value] for time,value in sorted(result.items())]


def _bpr(points, ratio, weekday_base=None, native_equal_profile=False):
    # Actual ComStock set_sch_bpr; constant profiles return sentinel base1.
    _number(ratio,'base_peak_ratio/ratio',0,1)
    if weekday_base is not None: _number(weekday_base,'base_peak_ratio/weekday_base',-math.inf)
    if not points: _error('base_peak_ratio','Source profile is empty')
    for time,value in points:
        _number(time,'base_peak_ratio/time',0,24)
        _number(value,'base_peak_ratio/value',-math.inf)
    if len(points)==1: return points,1.0
    peak=max(v for _,v in points); base=min(v for _,v in points)
    if peak==base:
        if not native_equal_profile:
            _error('base_peak_ratio','Unverified nonconstant equal-valued profile has undefined scale')
        # Source sf is nonfinite; (peak-val)*sf is NaN for every point.
        # Native clearValues restores [[24,0]], and addValue rejects NaN.
        # Verified against actual DOE/2007 Sunday profiles and public group draws.
        return [[24.0,0.0]],0.0
    new_base=ratio*peak
    if weekday_base is not None and weekday_base<new_base: new_base=weekday_base
    scale=(new_base-base)/(peak-base)
    result=[[time,_stored(max(0.0,(peak-value)*scale+value))] for time,value in points]
    return result,min(v for _,v in result)


def transform_commercial(channels: dict, operating: dict, source_context: dict) -> dict:
    """Transform original source arrays with explicitly bound inference context.

    Annual budgets are computed by the caller BEFORE this function and bind
    to its emitted arrays. Occupancy is multiplied by the source peak fraction;
    people counts and activity/temperature controls are not energy normalized.
    """
    context=copy.deepcopy(source_context)
    required=('year','holidays','steps_per_hour','configuration_id','standards_version','slot_modes',
              'slot_sources','occupancy_aggregation','occupancy_adjustment','source_clock')
    if not isinstance(context,dict): _error('source_context','Explicit source context object required')
    for key in required:
        if key not in context: _error('source_context/'+key,'Required dependency binding missing')
    configurations = {'medium_office_90_1_2007','medium_office_90_1_2013','medium_office_90_1_2019',
                      'medium_office_doe_ref_1980_2004','medium_office_doe_ref_pre_1980',
                      'small_office_90_1_2007','small_office_90_1_2013','small_office_90_1_2019',
                      'small_office_doe_ref_1980_2004','small_office_doe_ref_pre_1980'}
    if context['configuration_id'] not in configurations or context['standards_version']!='0.8.6':
        _error('configuration_id','Only audited Medium/Small Office/Standards0.8.6 bindings supported')
    if context['steps_per_hour']!=6 or isinstance(context['steps_per_hour'],bool):
        _error('steps_per_hour','Native validated timestep6 representation required')
    if context['holidays']!=[]: _error('holidays','Unvalidated commercial holiday inference context')
    if context['source_clock']!={'TZ':'UTC','variant':'controlled_no_DST_local_standard_calendar'}:
        _error('source_clock','Exact controlled local-standard reference clock required')
    if not isinstance(context['slot_sources'],dict) or not isinstance(context['slot_modes'],dict):
        _error('slot_sources','Explicit source rules and mode maps required')
    if not isinstance(channels,dict) or set(channels)!=set(context['slot_sources']) or set(channels)!=set(context['slot_modes']):
        _error('channels','Exact bound source channel/mode set required')
    adjustment=context['occupancy_adjustment']
    if (not isinstance(adjustment,dict) or adjustment.get('peak_occ_frac')!=.231
            or adjustment.get('source_key')!='comstock__resources__options_lookup_tsv'
            or adjustment.get('source_options')!=['baseline_hvac_sizing=autosize','baseline_hvac_sizing=hardsize']):
        _error('occupancy_adjustment','Exact selected source lookup binding required')
    effective=operating.get('effective_values') if isinstance(operating,dict) else None
    if not isinstance(effective,dict): _error('operating','Sampled source effective values required')
    operations={}
    for daytype in ('weekday','weekend'):
        start=_number(effective.get(daytype+'_start_time',{}).get('value'),'operating/start',0,86400)/3600
        duration=_number(effective.get(daytype+'_duration',{}).get('value'),'operating/duration',0,86400)/3600
        if any(effective.get(daytype+'_'+parameter,{}).get('unit')!='s' for parameter in ('start_time','duration')):
            _error('operating','Operating quantities require SI seconds')
        # Source CreateTypical truncates fractional-hour inputs to minutes.
        start=math.floor(start)+math.floor(60*(start%1))/60
        duration=math.floor(duration)+math.floor(60*(duration%1))/60
        points={}
        end=start+duration
        if end<24: points[start]=0.0; points[end]=1.0; points[24.0]=0.0
        else: points[end-24]=1.0; points[start]=0.0; points[24.0]=1.0
        operations[daytype]=_hoo([[time,value] for time,value in sorted(points.items()) if time>0])
    inference=_infer(context)
    output={}; special={}; transforms={}
    for slot,source in context['slot_sources'].items():
        raw=evaluate_rules(source,context['year'],[])['values']
        native_original=[value for day in range(365) for value in _hourly(_points(raw[day*24:day*24+24]),6)]
        values=channels[slot]
        if not isinstance(values,list) or len(values)!=8760:
            _error('channels/'+slot,'Original8760 hourly source values required')
        for i,(value,want) in enumerate(zip(values,raw)):
            _number(value,'channels/'+slot+'/'+str(i),-math.inf)
            if not (math.isclose(value,want,rel_tol=1e-9,abs_tol=1e-9) or value==native_original[i]):
                _error('channels/'+slot,'Original reference array differs from bound source rules')
        mode=context['slot_modes'][slot]
        if mode not in ('hours','tstat'): _error('slot_modes/'+slot,'Inspected hours/tstat mode required')
        ordinary=[rule for rule in source['rules'] if set(rule['day_types'].split('|')) &
                  {'Default','Wkdy','Wknd','Mon','Tue','Wed','Thu','Fri','Sat','Sun'}]
        floor=min(v for rule in ordinary for v in rule['values']); ceiling=max(v for rule in ordinary for v in rule['values'])
        daily=[]; cache={}
        for day in range(365):
            weekday=(date(context['year'],1,1)+timedelta(days=day)).weekday()
            kind='weekday' if weekday<5 else 'weekend'
            original=inference['daily_hoo'][day]; new=operations[kind]
            points=_points(raw[day*24:day*24+24])
            key=(tuple(map(tuple,points)),original['hoo_start'],original['hoo_end'],original['hoo_hours'],kind)
            if key not in cache:
                formula=_formula(points,original,floor,ceiling,mode)
                cache[key]=_apply(formula,new['hoo_start'],new['hoo_end'],floor,ceiling,1/6)
            daily.append(copy.deepcopy(cache[key]))
        if slot=='occupancy': daily=[[[t,_stored(v*.231)] for t,v in points] for points in daily]
        prefix={'lighting':'ltg_sch','additional_lighting':'ltg_sch','electric_equipment':'plugload_sch'}.get(slot)
        source_discards=[]
        if prefix:
            ratios={}
            for kind in ('weekday','weekend'):
                item=effective.get(prefix+'_'+kind+'_base_peak_ratio')
                if not isinstance(item,dict) or item.get('unit')!='1' or not isinstance(item.get('modify'),bool):
                    _error('operating/'+prefix,'Explicit sampled BPR value/NA flag required')
                ratios[kind]=_number(item.get('value'),'operating/ratio',0,1) if item['modify'] else None
                if not item['modify'] and item.get('value') is not None: _error('operating/ratio','NA requires null value')
            bases=[]
            for day in range(365):
                if (date(context['year'],1,1)+timedelta(days=day)).weekday()<5 and ratios['weekday'] is not None:
                    daily[day],base=_bpr(daily[day],ratios['weekday']); bases.append(base)
            if ratios['weekend'] is not None:
                if not bases: _error('operating/ratio','Native weekend BPR requires bound weekday base')
                for day in range(365):
                    if (date(context['year'],1,1)+timedelta(days=day)).weekday()>=5:
                        points=daily[day]
                        weekday=(date(context['year'],1,1)+timedelta(days=day)).weekday()
                        native_days={'medium_office_doe_ref_1980_2004':{6},'medium_office_doe_ref_pre_1980':{6},'medium_office_90_1_2007':{6},
                                     'small_office_90_1_2007':{5,6},'small_office_90_1_2013':{5,6},'small_office_90_1_2019':{5,6},
                                     'small_office_doe_ref_1980_2004':{6},'small_office_doe_ref_pre_1980':{6}}
                        verified=(weekday in native_days.get(context['configuration_id'],set())
                                  and slot in {'lighting','electric_equipment'}
                                  and len(points)>1 and max(v for _,v in points)==min(v for _,v in points)>0)
                        if verified:
                            source_discards.append({'day_of_year':day+1,'slot':slot,
                                'status':'native_nonfinite_values_rejected',
                                'source_locator':'ComStock:set_sch_bpr; OpenStudio ScheduleDay.clearValues/addValue',
                                'source_profile':copy.deepcopy(points),'rejected_value_count':len(points),
                                'source_method_evidence':copy.deepcopy(context.get('source_discard_method_evidence',{}).get(slot,{})),
                                'arithmetic':{'scale':'nonfinite','new_values':'NaN','encoding':'explicit_status_no_nonfinite_JSON_numbers'},
                                'native_default_profile':[[24.0,0.0]],
                                'interpretation':('Exact verified SmallOffice multi-point equal-positive '+('Saturday' if weekday==5 else 'Sunday')+' native storage result; original annual target retained' if context['configuration_id'].startswith('small_office_') else
                                    'Exact verified multi-point equal-positive Sunday native storage result; original annual target retained')})
                        daily[day],_=_bpr(points,ratios['weekend'],min(bases),native_equal_profile=verified)
        hourly_cache={}; annual=[]
        for points in daily:
            key=tuple(map(tuple,points))
            if key not in hourly_cache: hourly_cache[key]=_hourly(points,6)
            annual.extend(hourly_cache[key])
        output[slot]=annual
        specials={}
        for key in ('WntrDsn','SmrDsn'):
            candidates=[r for r in source['rules'] if key in r['day_types'].split('|')]
            specials[key]=_points(candidates[-1]['values']) if candidates else []
        special[slot]=specials
        transforms[slot]={'daily_profiles':daily,'mode':mode,'source_rule_order':copy.deepcopy(source['rules'])}
        if source_discards:
            transforms[slot]['source_discard_receipts']=source_discards
    context.update(inference=inference,operations=operations,special_profiles=special,transforms=transforms,
        operating_receipt=copy.deepcopy(operating),population_realization_equivalent=False,
        source_methods=['space.rb:spaces_get_occupancy_schedule/space_hours_of_operation',
            'parametric.rb:model_infer_hours_of_operation_building/schedule_ruleset_get_parametric_inputs/schedule_day_adjust_from_parameters',
            'ComStock:set_sch_bpr/schedule_ruleset_simple_value_adjust'],
        hourly_representation={'source':"Standards0.8.6 legacy minimum-interval getter; lexical version comparison selects3.10.0 <3.8.0",
                               'export_precision_decimals':5,'native_schedule_day_storage_significant_digits':15,
                               'get_value_query':'Snap forward to model timestep endpoint before No-interpolation source lookup',
                               'budget_binding':'Actual emitted8760 values; original raw frozen targets established before sampling/export rounding'})
    return {'channels':output,'source_context':context}
