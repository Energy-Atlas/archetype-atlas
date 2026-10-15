"""Coordinated ResStock occupancy, lighting, plug/TV and ceiling fan shapes.

Port of pinned schedules.rb:715-851,929-1075,1535-1564. No load magnitudes
or count/activity scaling is performed. Hourly arrays are raw source fractions.
"""
import calendar
import math

from ..errors import GeneratorError
from .activity import dates, required, rows

PRESENCE_KEYS = ('dishwasher','clothes_washer','clothes_dryer','cooking_range',
                 'plug_loads_other','plug_loads_tv','ceiling_fan','garage')
MONTHS = ('Jan','Feb','Mar','Apr','May','Jun','July','Aug','Sep','Oct','Nov','Dec')


def normalize(values, denominator=None):
    divisor = max(values) if denominator is None else denominator
    if not math.isfinite(divisor) or divisor <= 0:
        raise GeneratorError('source_undefined', '/channels', 'Upstream normalization has no positive denominator')
    return [value/divisor for value in values]


def shift_and_normalize(minutes, offset, days, shifts, denominator=None):
    """Upstream annual rotate -> daily monthly rotate -> hourly SUM -> normalize."""
    offset %= len(minutes)
    rotated = minutes[offset:]+minutes[:offset]
    hourly = []
    for i,today in enumerate(days):
        daytype = 'weekend' if today.weekday() >= 5 else 'weekday'
        lead = shifts[daytype][MONTHS[today.month-1]] % 1440
        day = rotated[i*1440:(i+1)*1440]
        day = day[lead:]+day[:lead]
        hourly.extend(math.fsum(day[j:j+60]) for j in range(0,1440,60))
    return normalize(hourly,denominator)


def _schedules(resources, key):
    return {(r[0],r[1]):[float(v) for v in r[2].split(',')]
            for r in rows(resources,key)[1:]}


def _finite(inputs,key,low,high):
    value=required(inputs,key)
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:
        raise GeneratorError('invalid_input','/inputs/'+key,'Finite source location value in range required')
    return value


def _state_month_shifts(resources, state):
    shifts={}
    for daytype in ('weekday','weekend'):
        table=rows(resources,daytype+'__state_and_monthly_schedule_shift_csv')
        header=table[0]
        shifts[daytype]={r[header.index('Month')]:int(r[header.index('Lead')]) for r in table[1:]
                         if r[header.index('State')]==state}
        if set(shifts[daytype])!=set(MONTHS):
            raise GeneratorError('unsupported_input','/inputs/state','State/month shifts not reported by source')
    return shifts


def _resident_fractions(activities):
    traces=activities['resident_states'];count=activities['simulated_residents']
    if len(traces)!=count or any(len(t)!=35040 or any(type(s) is not int or not 0<=s<7 for s in t) for t in traces):
        raise GeneratorError('activity_context','/activities/resident_states','Complete source state traces required')
    awake=[];home=[]
    for step in range(35040):
        away=sum(t[step]==5 for t in traces)/count
        sleeping=sum(t[step]==0 for t in traces)/count
        # Match source arithmetic and its per-resident fraction normalization.
        awake.append(1-(away+sleeping));home.extend([1-away]*15)
    return awake,home


def _interior_lighting_shape(awake, latitude, longitude, utc_offset, custom, offset, days, shifts):
    lighting=building_america_lighting(latitude,longitude,utc_offset,custom['lighting_interior','LightingInteriorMonthlyMultipliers'])
    minute_values=[]
    for i,today in enumerate(days):
        profile=lighting[today.month-1];minimum=min(profile)
        for step in range(96):
            value=minimum+(profile[step//4]-minimum)*awake[i*96+step]
            minute_values.extend([value]*15)
    return shift_and_normalize(minute_values,offset,days,shifts)


def building_america_lighting(latitude, longitude, utc_offset, seasonal):
    """Pinned source solar/location equation including its built-in seasonal offset.

    This offset belongs to the upstream lighting equation; no calendar DST
    conversion is applied. Source's >=51.49 latitude table remains explicit.
    """
    sunset=[]
    for month in range(1,13):
        if latitude < 51.49:
            julian=month*30-15
            declination=23.45*math.sin(0.9863*(284+julian)*0.01745329)
            deg=math.pi/180
            b=(julian-1)*0.9863
            equation=0.01667*(0.01719+0.42815*math.cos(deg*b)-7.35205*math.sin(deg*b)
                              -3.34976*math.cos(deg*2*b)-9.37199*math.sin(deg*2*b))
            try: angle=math.acos(-math.tan(deg*latitude)*math.tan(deg*declination))/deg
            except ValueError as error:
                raise GeneratorError('source_undefined','/inputs/latitude','Upstream solar equation is undefined at this location') from error
            offset=1 if 4<=month<=10 else 0
            sunset.append(offset+12.0+angle/15.0-equation-(-utc_offset*15+longitude)/15)
        else:
            sunset=[16.22214058,17.08642353,17.98324493,19.83547864,20.65149672,21.20662992,
                    21.12124777,20.37458274,19.25834757,18.08155615,16.14359164,15.75571306]
            break
    june=[.060,.040,.035,.025,.020,.020,.020,.020,.020,.020]
    profiles=[]
    for month in range(1,13):
        half=june+[0.0]*38
        for index in range(9,18):
            hour=(index+1.0)*.5
            half[index]=(half[8]-.15/(2*math.pi)*math.sin(2*math.pi*(hour-4.5)/3.5)+.15/3.5*(hour-4.5))*seasonal[month-1]
        for index in range(17,30):
            hour=(index+1.0)*.5
            half[index]=(half[16]-(-.02/(2*math.pi))*math.sin(2*math.pi*(hour-8.5)/5.5)+(-.02/5.5)*(hour-8.5))*seasonal[month-1]
        std=25.5/(abs(6.5-month)+20.0)*1.58679810983444
        def evening(hour):
            return .929707907917098*math.exp(-(hour-(sunset[month-1]+2.45016230615269))**2/(2*std**2))/(std*math.sqrt(2*math.pi))
        def late(hour):
            return .04+1.1372291802273*math.exp(-(hour-20.1501965859073)**2/(2*2.36567663279954**2))/(2.36567663279954*math.sqrt(2*math.pi))
        for index in range(29,46):
            half[index]=half[28]+evening((index+1.0)*.5)
        for index in range(45,47):
            hour=(index+1.0)*.5
            a=half[44]+evening(hour);b=late(hour)
            half[index]=min(a,b) if 20.1501965859073<sunset[month-1]+2.45016230615269 else max(a,b)
        for index in range(46,48):half[index]=late((index+1)*.5)
        profiles.append([half[h*2]+half[h*2+1] for h in range(24)])
    # Source monthly weighting simplifies to a shared scalar, which cancels
    # in initialize_interior_lighting_schedule's annual max normalization.
    peak=max(max(profile) for profile in profiles)
    return [[value/peak for value in profile] for profile in profiles]


def occupancy_shapes(activities: dict, inputs: dict, resources) -> dict:
    days=dates(required(inputs,'year'))
    if (activities['year']!=inputs['year'] or activities['resource_set_id']!=resources.resource_set_id
            or activities['residents_input']!=required(inputs,'residents')):
        raise GeneratorError('activity_context','/activities','Activities differ from requested calendar/residents/resource context')
    context={'activity_status':activities['status'],'unit_offset_minutes':activities['unit_offset_minutes'],
             'simulated_residents':activities['simulated_residents'], 'residents_input':activities['residents_input'],
             'resource_set_id':resources.resource_set_id,'export_precision':'raw_source_float',
             'shift_order':['annual_unit_minute_rotation','daily_state_month_rotation','hourly_sum','source_normalization']}
    if activities['status']=='upstream_zero_residents_skip':
        context['rng_consumed']=False
        return {'channels':{'occupants':[0.0]*8760},'source_context':context}
    state=required(inputs,'state')
    shifts=_state_month_shifts(resources,state)
    installed=required(inputs,'installed')
    if not isinstance(installed,dict) or set(installed)!=set(PRESENCE_KEYS) or any(type(v) is not bool for v in installed.values()):
        raise GeneratorError('invalid_input','/inputs/installed','Exact source presence booleans required')
    latitude=_finite(inputs,'latitude',-90,90);longitude=_finite(inputs,'longitude',-180,180)
    utc_offset=_finite(inputs,'time_zone_utc_offset',-14,14)
    weather_id=required(inputs,'weather_id');weather=resources.get('weather',weather_id)
    drybulb=weather['drybulb_C']
    if len(drybulb)!=8760 or any(not math.isfinite(v) for v in drybulb):
        raise GeneratorError('resource_integrity','/weather/'+weather_id,'Source hourly drybulbs required')
    fan_months=[];start=0
    for month in range(1,13):
        hours=calendar.monthrange(inputs['year'],month)[1]*24
        average=math.fsum(drybulb[start:start+hours])/hours
        fan_months.append(int(average*1.8+32>63.0));start+=hours
    awake,home=_resident_fractions(activities)
    offset=activities['unit_offset_minutes']
    channels={'occupants':shift_and_normalize(home,offset,days,shifts,60)}
    custom=_schedules(resources,'schedules_csv')
    defaults=_schedules(resources,'resources__hpxml-measures__HPXMLtoOpenStudio__resources__data__default_schedules_csv')
    specifications={
        'plug_loads_other':(defaults['plug_loads_other','WeekdayScheduleFractions'],defaults['plug_loads_other','WeekendScheduleFractions'],custom['plug_loads_other','PlugLoadsOtherMonthlyMultipliers']),
        'plug_loads_tv':(custom['plug_loads_tv','PlugLoadsTVWeekdayFractions'],custom['plug_loads_tv','PlugLoadsTVWeekendFractions'],custom['plug_loads_tv','PlugLoadsTVMonthlyMultipliers']),
        'ceiling_fan':(defaults['ceiling_fan','WeekdayScheduleFractions'],defaults['ceiling_fan','WeekendScheduleFractions'],fan_months)}
    for slot,(weekday,weekend,monthly) in specifications.items():
        if not installed[slot]:continue
        minute_values=[]
        for i,today in enumerate(days):
            profile=weekend if today.weekday()>=5 else weekday
            minimum=min(profile)
            for step in range(96):
                full=profile[step//4]*monthly[today.month-1]
                value=minimum+(full-minimum)*awake[i*96+step]
                minute_values.extend([value]*15)
        channels[slot]=shift_and_normalize(minute_values,offset,days,shifts)
    channels['lighting_interior']=_interior_lighting_shape(awake,latitude,longitude,utc_offset,custom,offset,days,shifts)
    if installed['garage']:channels['lighting_garage']=list(channels['lighting_interior'])
    context.update(state=state,monthly_shifts=shifts,installed=dict(installed),fan_months=fan_months,
                   weather_id=weather_id,weather_provenance=weather['provenance'],latitude=latitude,
                   longitude=longitude,time_zone_utc_offset=utc_offset,rng_consumed=False)
    return {'channels':channels,'source_context':context}
