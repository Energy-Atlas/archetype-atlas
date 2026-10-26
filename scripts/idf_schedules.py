"""Evaluate IDF Schedule:Compact and atlas rulesets over a full year, holidays and design days.

Both are evaluated on one calendar: a year (default 2006, which starts on a Sunday,
as the DOE reference run periods do) with the IDF's RunPeriodControl:SpecialDays
holidays, plus one summer and one winter design day. Values are hourly means, so
a compact "Until" time inside an hour becomes an energy-conserving mean.

Atlas rulesets follow the Program JSON contract: the last matching specific rule
wins, otherwise the last applicable Default rule; a holiday matches only Hol
rules and otherwise takes Default. (atlas_schedules.calendar implements the
openstudio-standards generation rule instead, which never applies holidays.)

The residential and manufactured-housing prototypes also use Schedule:Year,
Schedule:Week:Compact / Daily, Schedule:Day:Hourly / Interval / List and
Schedule:Constant (`Schedules`). `Schedules.ruleset` converts any of them to atlas
rules, and `Schedules.checked_ruleset` evaluates the rules against the source
objects on every day of the year and both design days before returning them.
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
        elif re.match(r'until:? ?\d', low):
            # The PNNL residential files also write "Until 24:00" without a colon.
            hour, minute = re.sub(r'^until:? ?', '', low).split(':')
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


# Schedule:Year, Schedule:Week:* and Schedule:Day:* (residential and manufactured-housing prototypes)

KINDS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Hol', 'SmrDsn', 'WntrDsn')
DAILY_ORDER = ('Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Hol', 'SmrDsn', 'WntrDsn', 'CustomDay1', 'CustomDay2')
WEEK_TOKENS = {'sunday': ('Sun',), 'monday': ('Mon',), 'tuesday': ('Tue',), 'wednesday': ('Wed',),
               'thursday': ('Thu',), 'friday': ('Fri',), 'saturday': ('Sat',),
               'weekdays': ('Mon', 'Tue', 'Wed', 'Thu', 'Fri'), 'weekday': ('Mon', 'Tue', 'Wed', 'Thu', 'Fri'),
               'weekends': ('Sat', 'Sun'), 'weekend': ('Sat', 'Sun'), 'holiday': ('Hol',), 'holidays': ('Hol',),
               'summerdesignday': ('SmrDsn',), 'winterdesignday': ('WntrDsn',),
               'customday1': ('CustomDay1',), 'customday2': ('CustomDay2',),
               'alldays': DAILY_ORDER}
RULE_YEAR = 2000  # atlas rule dates are month/day on a leap-capable calendar
SCHEDULE_CLASSES = ('schedule:compact', 'schedule:constant', 'schedule:year', 'schedule:week:compact',
                    'schedule:week:daily', 'schedule:day:hourly', 'schedule:day:interval', 'schedule:day:list')


def until_minutes(text):
    hour, minute = re.sub(r'^until:? ?', '', re.sub(r'\s+', ' ', text.lower()).strip()).split(':')
    return int(hour) * 60 + int(minute)


class Schedules:
    """The schedule objects of one parsed IDF (idf_reader.parse), by lower-case name."""

    def __init__(self, objects):
        self.objects = {}
        for cls, fields in objects:
            if cls in SCHEDULE_CLASSES and fields:
                self.objects[fields[0].lower()] = (cls, fields)
        self._days, self._weeks = {}, {}

    def cls(self, name):
        return self.objects[name.lower()][0]

    def fields(self, name):
        return self.objects[name.lower()][1]

    def day(self, name):
        """24 hourly means of a Schedule:Day:* object."""
        if name.lower() not in self._days:
            self._days[name.lower()] = self._day(name)
        return list(self._days[name.lower()])

    def _day(self, name):
        cls, fields = self.objects[name.lower()]
        if cls == 'schedule:day:hourly':
            values = [float(v) for v in fields[2:26]]
            if len(values) != 24:
                raise ValueError(f'Schedule:Day:Hourly {fields[0]} has {len(values)} values')
            return values
        if cls == 'schedule:day:interval':
            if fields[2].strip().lower() not in ('', 'no'):
                raise ValueError(f'Interpolated Schedule:Day:Interval {fields[0]} is not supported')
            steps = [[until_minutes(fields[i]), float(fields[i + 1])] for i in range(3, len(fields) - 1, 2) if fields[i]]
            return hourly_means(steps)
        if cls == 'schedule:day:list':
            if fields[2].strip().lower() not in ('', 'no'):
                raise ValueError(f'Interpolated Schedule:Day:List {fields[0]} is not supported')
            step = int(float(fields[3]))
            values = [float(v) for v in fields[4:] if v != '']
            if step * len(values) != 1440:
                raise ValueError(f'Schedule:Day:List {fields[0]} does not cover the day')
            return hourly_means([[step * (i + 1), v] for i, v in enumerate(values)])
        raise ValueError(f'{fields[0]} is a {cls}, not a day schedule')

    def week(self, name):
        """{day kind: Schedule:Day name} of a Schedule:Week:Compact or Schedule:Week:Daily."""
        if name.lower() not in self._weeks:
            self._weeks[name.lower()] = self._week(name)
        return dict(self._weeks[name.lower()])

    def _week(self, name):
        cls, fields = self.objects[name.lower()]
        if cls == 'schedule:week:daily':
            return {kind: day for kind, day in zip(DAILY_ORDER, fields[1:]) if day}
        if cls != 'schedule:week:compact':
            raise ValueError(f'{fields[0]} is a {cls}, not a week schedule')
        out = {}
        for i in range(1, len(fields) - 1, 2):
            tokens = re.sub(r'^for:? ?', '', re.sub(r'\s+', ' ', fields[i].lower()).strip()).split()
            if tokens == ['allotherdays']:
                kinds = [k for k in DAILY_ORDER if k not in out]
            else:
                kinds = [k for t in tokens for k in WEEK_TOKENS[t]]
            for kind in kinds:
                out.setdefault(kind, fields[i + 1])
        return out

    def periods(self, name):
        """[(start (month, day), end (month, day), week name)] of a Schedule:Year."""
        rows = self.fields(name)[2:]
        return [((int(rows[i + 1]), int(rows[i + 2])), (int(rows[i + 3]), int(rows[i + 4])), rows[i])
                for i in range(0, len(rows) - 4, 5) if rows[i]]

    def evaluate(self, name, days):
        """{day key: 24 hourly means or None} over a calendar from calendar_days."""
        cls, fields = self.objects[name.lower()]
        if cls == 'schedule:compact':
            return evaluate_compact(fields, days)[0]
        if cls == 'schedule:constant':
            return {key: [float(fields[2])] * 24 for key in days}
        if cls != 'schedule:year':
            raise ValueError(f'{fields[0]} is a {cls}; loads reference compact, constant or year schedules')
        periods = self.periods(name)
        out = {}
        for key, (date, kind) in days.items():
            period = next((p for p in periods if p[0] <= (date.month, date.day) <= p[1]), None)
            day = self.week(period[2]).get(kind) if period else None
            out[key] = self.day(day) if day else None
        return out

    def ruleset(self, name):
        """Atlas rules (last matching specific rule wins, else the last Default) for a schedule."""
        cls, fields = self.objects[name.lower()]
        if cls == 'schedule:constant':
            return [rule('Default', (1, 1), (12, 31), [float(fields[2])])]
        if cls == 'schedule:compact':
            return compact_ruleset(fields)
        if cls != 'schedule:year':
            raise ValueError(f'{fields[0]} is a {cls}; loads reference compact, constant or year schedules')
        rules = []
        for start, end, week in self.periods(name):
            days = self.week(week)
            missing = [k for k in KINDS if k not in days]
            if missing:
                raise ValueError(f'Week {week} of {fields[0]} has no day schedule for {missing}')
            counts = {}
            for kind in KINDS:
                counts[days[kind]] = counts.get(days[kind], 0) + 1
            # The day schedule of most kinds is the Default; ties go to the earliest kind.
            first = {d: min(KINDS.index(k) for k in KINDS if days[k] == d) for d in counts}
            default = max(counts, key=lambda d: (counts[d], -first[d]))
            rules.append(rule('Default', start, end, self.day(default)))
            groups = {}
            for kind in KINDS:
                if days[kind] != default:
                    groups.setdefault(days[kind], []).append(kind)
            for day, kinds in groups.items():
                rules.append(rule(day_types(kinds), start, end, self.day(day)))
        return rules

    def checked_ruleset(self, name, days=None):
        """The ruleset, after checking it against the source objects on every day and both design days."""
        days = days or calendar_days([])
        rules = self.ruleset(name)
        expected = self.evaluate(name, days)
        got = evaluate_ruleset(rules, lambda r: r['values'] * (24 // len(r['values'])), days)
        bad = [k for k in days if not (expected[k] is None and got[k] is None) and not same(expected[k], got[k])]
        if bad:
            raise ValueError(f'Converted {name} differs from its source on {bad[:3]}')
        return rules


def day_types(kinds):
    """Atlas day-type tokens for a set of day kinds, with Wkdy and Wknd where they apply."""
    kinds = list(kinds)
    tokens = []
    if all(k in kinds for k in KINDS[:5]):
        tokens.append('Wkdy')
        kinds = [k for k in kinds if k not in KINDS[:5]]
    if all(k in kinds for k in ('Sat', 'Sun')):
        tokens.append('Wknd')
        kinds = [k for k in kinds if k not in ('Sat', 'Sun')]
    return '|'.join(tokens + kinds)


def rule(tokens, start, end, values):
    values = [round(v, 10) for v in values]
    constant = len(set(values)) == 1
    return {'day_types': tokens, 'start_date': f'{RULE_YEAR}-{start[0]:02d}-{start[1]:02d}',
            'end_date': f'{RULE_YEAR}-{end[0]:02d}-{end[1]:02d}', 'type': 'Constant' if constant else 'Hourly',
            'values': values[:1] if constant else values}


def compact_ruleset(fields):
    """Atlas rules for a Schedule:Compact: each Through period's For lines in reverse, AllOtherDays as Default."""
    rules, start = [], (1, 1)
    for (month, day), block in compact_rules(fields):
        period, covered = [], set()
        for tokens, steps in block:
            if tokens == ['allotherdays']:
                kinds = [k for k in KINDS if k not in covered]
            else:
                kinds = [k for t in tokens for k in WEEK_TOKENS.get(t, ()) if k in KINDS and k not in covered]
            name = 'Default' if tokens == ['allotherdays'] or set(kinds) == set(KINDS) else day_types(kinds)
            covered |= set(kinds)
            if kinds:
                period.append(rule(name, start, (month, day), hourly_means(steps)))
        defaults = [r for r in period if r['day_types'] == 'Default']
        rules += defaults + [r for r in reversed(period) if r['day_types'] != 'Default']
        following = dt.date(2001, month, 28 if (month, day) == (2, 29) else day) + dt.timedelta(days=1)
        start = (following.month, following.day)
    return rules
