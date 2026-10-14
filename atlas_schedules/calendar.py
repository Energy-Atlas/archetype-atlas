"""Adapter for inspected frozen Standards rules; not a residential activity layer.

Standards.Model#model_add_schedule creates specific rules in source order
(newest has highest priority). Default and design days are source-provided
profiles; no implicit holiday calendar, DST, or invented residential profiles.
The pinned method ignores Hol rows; explicit holiday dates select the source
default day. Unused Hol metadata stays in the caller's original rule objects.
"""
import calendar as _calendar
from datetime import date,datetime,timedelta
import math
from .errors import GeneratorError

_DAYS=('Mon','Tue','Wed','Thu','Fri','Sat','Sun')
_SELECTORS=set(_DAYS)|{'Default','Wkdy','Wknd','WntrDsn','SmrDsn','Hol'}

def _error(path,message):
    raise GeneratorError('invalid_calendar',path,message)

def _month_day(value,path):
    if not isinstance(value,str):_error(path,'Source rule date required')
    try:
        if len(value)==5:parsed=date.fromisoformat('2000-'+value)
        elif len(value)==10:parsed=date.fromisoformat(value)
        else:parsed=datetime.fromisoformat(value).date()
    except ValueError as error:
        raise GeneratorError('invalid_calendar',path,'Invalid source Gregorian date') from error
    return parsed.month,parsed.day

def evaluate_rules(schedule: dict, year: int, holidays: list[str]) -> dict:
    if isinstance(year,bool) or not isinstance(year,int) or not 1<=year<=9999:
        _error('/calendar/year','Gregorian year from 1 through 9999 required')
    if _calendar.isleap(year):
        raise GeneratorError('leap_year','/calendar/year','Non-leap Gregorian year required')
    if not isinstance(holidays,list):_error('/calendar/holidays','Explicit date list required')
    holiday_dates=set()
    for i,value in enumerate(holidays):
        if not isinstance(value,str) or len(value)!=10:_error(f'/calendar/holidays/{i}','ISO Gregorian date required')
        try:parsed=date.fromisoformat(value)
        except ValueError as error:raise GeneratorError('invalid_calendar',f'/calendar/holidays/{i}','Invalid holiday date') from error
        if parsed.year!=year or parsed in holiday_dates:_error(f'/calendar/holidays/{i}','Holiday outside year or duplicated')
        holiday_dates.add(parsed)
    if not isinstance(schedule,dict) or schedule.get('time_resolution_minutes')!=60:
        _error('/schedule/time_resolution_minutes','Source hourly rule object required')
    if schedule.get('interpolation','No') not in ('No',False,'none','step'):
        _error('/schedule/interpolation','Only inspected stepwise source profiles supported')
    rules=schedule.get('rules')
    if not isinstance(rules,list) or not rules:_error('/schedule/rules','Source rules required')
    compiled=[];default=None;special={}
    for i,rule in enumerate(rules):
        path=f'/schedule/rules/{i}'
        if not isinstance(rule,dict):_error(path,'Source rule object required')
        tokens=rule.get('day_types')
        if isinstance(tokens,str):tokens=tokens.split('|')
        if not isinstance(tokens,list) or not tokens or any(not isinstance(t,str) or t not in _SELECTORS for t in tokens):
            _error(path+'/day_types','Unknown source selector')
        values=rule.get('values')
        if not isinstance(values,list) or len(values) not in (1,24) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
            _error(path+'/values','One constant or 24 finite hourly source values required')
        kind=rule.get('type','Constant' if len(values)==1 else 'Hourly')
        if kind not in ('Constant','Hourly') or (kind=='Hourly' and len(values)!=24):
            _error(path+'/type','Only inspected Constant/Hourly source rules supported')
        profile=[values[0]]*24 if kind=='Constant' else list(values)
        start=_month_day(rule.get('start_date'),path+'/start_date');end=_month_day(rule.get('end_date'),path+'/end_date')
        if 'Default' in tokens:default=profile
        for key in ('WntrDsn','SmrDsn'):
            if key in tokens:special[key]=profile
        # Hol is ignored by the pinned Standards method, not converted to a new profile.
        compiled.append((set(tokens),start,end,profile))
    # Standards creates an empty defaultDaySchedule when no Default row exists.
    # Its native getValue is zero (independently captured); this does not supply
    # missing defaults to other companion objects.
    if default is None and all(r.get('type') in ('Constant','Hourly') for r in rules):
        default=[0.0]*24
    annual=[]
    for day_index in range(365):
        day=date(year,1,1)+timedelta(days=day_index);month_day=(day.month,day.day);selected=default
        if day not in holiday_dates:
            for tokens,start,end,profile in compiled:
                active=start<=month_day<=end if start<=end else month_day>=start or month_day<=end
                weekday=day.weekday()
                if active and (_DAYS[weekday] in tokens or weekday<5 and 'Wkdy' in tokens or weekday>=5 and 'Wknd' in tokens):
                    selected=profile
        if selected is None:_error('/schedule/rules',f'No source day profile for {day.isoformat()}')
        annual.extend(selected)
    result={'values':annual}
    if special:result['special_profiles']=special
    return result
