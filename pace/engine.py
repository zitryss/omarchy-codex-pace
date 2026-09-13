"""Provider instants and exact percentage-point arithmetic; no presentation rounding in ledger."""
import calendar
from datetime import datetime, timedelta
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
                observed=opening - remaining if opening is not None else None)


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
    for i in range(7):
        begin = start + i * WEEK // 7
        finish = start + (i + 1) * WEEK // 7
        record = records[i]
        p = record.get('plan')
        if active is not None and i > active:
            p = BASE
        entry = dict(id=i, plan=whole(p), observed=whole(record.get('observed')),
                     future=active is not None and i > active, active=i == active,
                     detail=f'{local(begin):%a %d %b %H:%M %Z} – {local(finish):%a %d %b %H:%M %Z}\n{record.get("quality", "Opening unknown")}')
        entries.setdefault(local(begin).date(), []).append(entry)
    if active is not None:
        first = min(first, min(entries))
        last = max(last, max(entries))
    first -= timedelta(days=first.weekday())
    last += timedelta(days=6-last.weekday())
    cells = []
    for n in range((last-first).days+1):
        day = first + timedelta(days=n)
        es = entries.get(day, [])
        cells.append(dict(date=day.isoformat(), day=day.day, muted=day.month != today.month,
                          entries=es, highlighted=bool(es), active=any(e['active'] for e in es),
                          detail='\n\n'.join(e['detail'] + f'\nP {e["plan"]} · O {e["observed"]}' for e in es)))
    return local(now).strftime('%B %Y'), cells
