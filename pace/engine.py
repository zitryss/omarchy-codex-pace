"""Provider instants and exact percentage-point arithmetic; no presentation rounding in ledger."""
import calendar
from datetime import datetime, timedelta, time
from fractions import Fraction

WEEK = 604800
BASE = Fraction(100, 7)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError('Invalid numeric reading')
    return Fraction(str(value))


def whole(value):
    if value is None or value < 0:
        return '—'
    return str(value.numerator // value.denominator) if isinstance(value, Fraction) else str(int(value // 1))


def index(start, end, now):
    if end - start != WEEK or not start <= now < end:
        return None
    return min(6, int((now - start) // (WEEK // 7)))


def budget(remaining, i, opening=None):
    reserve = Fraction(100 * (6 - i), 7)
    signed = remaining - reserve
    available = max(Fraction(0), signed)
    plan = max(Fraction(0), opening - reserve) if opening is not None else None
    ratio = 100 * available / plan if plan else None
    return dict(available=available, plan=plan, ratio=ratio, debt=max(Fraction(0), -signed),
                used=opening - remaining if opening is not None else None)


def countdown(seconds):
    if seconds <= 0:
        return '—'
    if seconds < 60:
        return '<1m'
    minutes = int(seconds // 60)
    return f'{minutes // 60}h {minutes % 60:02d}m'


def month_cells(start, end, now, records, tz=None):
    local = lambda t: datetime.fromtimestamp(t, tz)
    today = local(now).date()
    first = today.replace(day=1)
    last = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    entries = {}
    active = index(start, end, now)
    intervals = [(start+i*WEEK//7, start+(i+1)*WEEK//7) for i in range(7)]
    for i, (begin, finish) in enumerate(intervals):
        record = records[i]
        p = BASE if active is not None and i > active else record.get('plan')
        entry = dict(id=i, plan=whole(p), used=whole(record.get('used')),
                     future=active is not None and i > active,
                     detail=f'{local(begin):%a %d %b %H:%M %Z} – {local(finish):%a %d %b %H:%M %Z}\n{record.get("quality", "Bucket opening balance unavailable.")}')
        entries.setdefault(local(begin).date(), []).append(entry)
    if active is not None:
        first = min(first, local(start).date())
        last = max(last, local(end-0.000001).date())
    first -= timedelta(days=first.weekday())
    last += timedelta(days=6-last.weekday())
    cells = []
    for n in range((last-first).days+1):
        day = first + timedelta(days=n)
        # Convert each midnight separately: civil days need not last 86400 seconds.
        midnight = datetime.combine(day, time.min, tz).timestamp()
        next_midnight = datetime.combine(day+timedelta(days=1), time.min, tz).timestamp()
        overlaps = lambda a, b: max(midnight,a) < min(next_midnight,b)
        es = entries.get(day, [])
        touched = overlaps(start,end)
        active_day = active is not None and overlaps(*intervals[active])
        descriptions = []
        for i, (a,b) in enumerate(intervals):
            if overlaps(a,b):
                descriptions.append(f'Virtual bucket {i+1}: {local(a):%d %b %H:%M %Z} – {local(b):%d %b %H:%M %Z}')
        descriptions.extend(e['detail'] + f'\nP {e["plan"]} · U {e["used"]}' for e in es)
        if touched and not es:
            descriptions.append('Overlap only; no bucket starts on this date.')
        cells.append(dict(date=day.isoformat(), day=day.day, muted=(day.year,day.month) != (today.year,today.month),
                          entries=es, highlighted=touched, active=active_day, today=day==today,
                          detail='\n\n'.join(descriptions)))
    return local(now).strftime('%B %Y'), cells
