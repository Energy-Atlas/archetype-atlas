"""Evaluate IDF Schedule:Compact and atlas rulesets over a full year, holidays and design days.

Both are evaluated on one calendar: a year (default 2006, which starts on a Sunday,
as the DOE reference run periods do) with the IDF's RunPeriodControl:SpecialDays
holidays, plus one summer and one winter design day. Values are hourly means, so
a compact "Until" time inside an hour becomes an energy-conserving mean.

Atlas rulesets follow the Program JSON contract: the last matching specific rule
wins, otherwise the last applicable Default rule; a holiday matches only Hol
rules and otherwise takes Default. (atlas_schedules.calendar implements the
openstudio-standards generation rule instead, which never applies holidays.)
"""
import calendar
import datetime as dt
import re

WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
TOLERANCE = 1e-6
MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})  # 'Jan 1' (PNNL IECC files)
ORDINALS = {'1st': 1, 'first': 1, '2nd': 2, 'second': 2, '3rd': 3, 'third': 3, '4th': 4, 'fourth': 4, 'last': -1}


def holiday_date(text, year):
    """'January 1', '1/1', '3rd Monday in January' or 'Last Monday in May'."""
    t = text.strip().lower()
    match = re.fullmatch(r'(\d+)/(\d+)', t)
    if match:
        return dt.date(year, int(match.group(1)), int(match.group(2)))
    match = re.fullmatch(r'([a-z]+)\s+(\d+)', t)
    if match:
        return dt.date(year, MONTHS[match.group(1)], int(match.group(2)))
    match = re.fullmatch(r'(\w+)\s+([a-z]+)\s+in\s+([a-z]+)', t)
    nth, weekday, month = ORDINALS[match.group(1)], match.group(2)[:3].capitalize(), MONTHS[match.group(3)]
    days = [dt.date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1)
            if WEEKDAYS[dt.date(year, month, d).weekday()] == weekday]
    return days[nth - 1] if nth > 0 else days[-1]


def calendar_days(holidays, year=2006):
    """{key: (date, kind)} for every day of the year plus 'SmrDsn' and 'WntrDsn'."""
    holiday_dates = {holiday_date(text, year) for _, text in holidays}
    result = {}
    day = dt.date(year, 1, 1)
    while day.year == year:
        result[day.isoformat()] = (day, 'Hol' if day in holiday_dates else WEEKDAYS[day.weekday()])
        day += dt.timedelta(days=1)
    result['SmrDsn'] = (dt.date(year, 7, 21), 'SmrDsn')
    result['WntrDsn'] = (dt.date(year, 1, 21), 'WntrDsn')
    return result


def compact_rules(fields):
    """[((month, day) through, [(for tokens, [(until minute, value)])])]."""
    periods = []
    for field in fields[2:]:
        low = re.sub(r'\s+', ' ', field.lower()).strip()
        if low.startswith('through:'):
            month, day = low[8:].strip().split('/')
            periods.append(((int(month), int(day)), []))
        elif re.match(r'for:? ', low) or low.startswith('for:'):
            # The DOE files also write "For WinterDesignDay" without a colon.
            periods[-1][1].append((re.sub(r'^for:? ?', '', low).split(), []))
        elif low.startswith('until:'):
            hour, minute = low[6:].strip().split(':')
            periods[-1][1][-1][1].append([int(hour) * 60 + int(minute), None])
        elif low.startswith('interpolate:'):
            continue
        else:
            periods[-1][1][-1][1][-1][1] = float(field)
    return periods


def compact_tokens(kind):
    """Compact day-type tokens that select a day of the given kind."""
    if kind == 'Hol':
        return {'holiday', 'holidays', 'alldays'}
    if kind == 'SmrDsn':
        return {'summerdesignday', 'alldays'}
    if kind == 'WntrDsn':
        return {'winterdesignday', 'alldays'}
    weekday = {'Mon': 'monday', 'Tue': 'tuesday', 'Wed': 'wednesday', 'Thu': 'thursday', 'Fri': 'friday',
               'Sat': 'saturday', 'Sun': 'sunday'}[kind]
    tokens = {weekday, 'alldays'}
    if kind in ('Sat', 'Sun'):
        tokens |= {'weekends', 'weekend'} | ({'saturdays'} if kind == 'Sat' else set())
    else:
        tokens |= {'weekdays', 'weekday'}
    return tokens


def hourly_means(steps):
    minutes = []
    start = 0
    for until, value in steps:
        minutes.extend([value] * (until - start))
        start = until
    return [sum(minutes[h * 60:(h + 1) * 60]) / 60 for h in range(24)]


def evaluate_compact(fields, days):
    """{day key: 24 hourly means or None}, and whether any change falls inside an hour."""
    periods = compact_rules(fields)
    result = {}
    subhour = False
    for key, (date, kind) in days.items():
        block = next(rules for through, rules in periods if (date.month, date.day) <= through)
        wanted = compact_tokens(kind)
        rule = next((r for r in block if wanted & set(r[0])), None) or \
            next((r for r in block if 'allotherdays' in r[0]), None)
        if rule is None:
            result[key] = None
            continue
        subhour |= any(until % 60 for until, _ in rule[1][:-1])
        result[key] = hourly_means(rule[1])
    return result, subhour


def month_day(text):
    return int(text[5:7]), int(text[8:10])


def ruleset_tokens(kind):
    if kind in ('Hol', 'SmrDsn', 'WntrDsn'):
        return {kind}
    return {kind, 'Wkdy' if kind not in ('Sat', 'Sun') else 'Wknd'}


def covers(rule, date):
    start, end = month_day(rule['start_date']), month_day(rule['end_date'])
    d = (date.month, date.day)
    return start <= d <= end if start <= end else d >= start or d <= end


def evaluate_ruleset(rules, profile, days):
    """{day key: 24 values or None} for atlas rules; profile(rule) gives a rule's 24 values."""
    result = {}
    for key, (date, kind) in days.items():
        applicable = [r for r in rules if covers(r, date)]
        wanted = ruleset_tokens(kind)
        specific = [r for r in applicable if wanted & set(r['day_types'].split('|'))]
        default = [r for r in applicable if 'Default' in r['day_types'].split('|')]
        rule = specific[-1] if specific else (default[-1] if default else None)
        result[key] = None if rule is None else profile(rule)
    return result


def same(a, b):
    return a is not None and b is not None and all(abs(x - y) <= TOLERANCE for x, y in zip(a, b))


def differing_days(left, right):
    return [key for key in left if not same(left[key], right.get(key))]


def classify(keys, days):
    """identical, holidays only, design days only, holidays and design days only, or profile."""
    if not keys:
        return 'identical'
    kinds = {days[k][1] for k in keys}
    if kinds <= {'Hol'}:
        return 'holidays only'
    if kinds <= {'SmrDsn', 'WntrDsn'}:
        return 'design days only'
    if kinds <= {'Hol', 'SmrDsn', 'WntrDsn'}:
        return 'holidays and design days only'
    return 'profile'
