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



def pacing(remaining, active, records):
    """Read-only pacing estimates. Never write these values back into source history."""
    projected = [dict(record, usedEstimated=False) for record in records]
    for record in projected:
        if record.get('plan') is None:
            record['plan'] = BASE
            record['planBasis'] = 'Based on the standard daily plan; bucket opening balance unavailable.'
        else:
            record['planBasis'] = 'Based on the supported bucket opening balance.'
        record['usedBasis'] = 'Net reported usage supported by opening and balance evidence.'
        if record.get('used') is None:
            record['usedBasis'] = 'Full-bucket usage unavailable.'
        elif record['used'] < 0:
            record['usedBasis'] = 'Provider balance correction; not negative consumption.'

    current = projected[active]
    fallback = current.get('opening') is None
    result = budget(remaining, active, current.get('opening'))
    if fallback:
        result.update(plan=BASE, ratio=100 * result['available'] / BASE,
                      used=max(Fraction(0), BASE - result['available']))
        current['usedEstimated'] = True
        current['usedBasis'] = ('Estimated shortfall against the standard daily allowance: max(0, 100/7 - available). '
                                'Earlier overspending may contribute; this is not measured bucket consumption.')
    current.update(plan=result['plan'], used=result['used'])

    # Supported full-bucket history is immutable. Only completed unknown entries
    # may share the residual from THIS provider epoch's latest reported balance.
    measured = [record['used'] for record in projected[:active] if record.get('used') is not None]
    eligible = [record for record in projected[:active] if record.get('used') is None]
    residual = 100 - remaining - sum(measured, Fraction(0)) - result['used']
    diagnostic = ''
    if any(value < 0 for value in measured) or result['used'] < 0:
        diagnostic = 'Balance corrections prevent a coherent historical usage estimate.'
    elif residual < 0:
        diagnostic = 'Usage evidence exceeds reported week usage; historical estimates unavailable.'
    elif eligible:
        for record in eligible:
            record.update(used=residual / len(eligible), usedEstimated=True,
                          usedBasis='Estimated equal share of residual reported week usage across completed buckets with missing usage. Not reconstructed consumption.')
    elif residual != 0:
        diagnostic = 'Residual reported week usage has no eligible completed bucket; left unallocated.'
    for record in projected[active+1:]:
        record.update(used=None, usedEstimated=False, usedBasis='Future usage unavailable.')
    return result, projected, dict(fallback=fallback, residual=str(residual), diagnostic=diagnostic)

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
        p = record.get('plan')
        if p is None:
            p = BASE
        entry = dict(id=i, plan=whole(p), used=whole(record.get('used')),
                     future=active is not None and i > active, usedEstimated=record.get('usedEstimated', False),
                     detail=f'{local(begin):%a %d %b %H:%M %Z} – {local(finish):%a %d %b %H:%M %Z}\n{record.get("quality", "Bucket opening balance unavailable.")}')
        entry['detail'] += '\n' + record.get('planBasis', 'Standard daily plan' if record.get('plan') is None else 'Supported opening plan')
        entry['detail'] += '\n' + record.get('usedBasis', 'Usage unavailable.')
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
        descriptions.extend(e['detail'] + f'\nP {e["plan"]} · U {e["used"]}' + ('* estimated' if e['usedEstimated'] else '') for e in es)
        if touched and not es:
            descriptions.append('Overlap only; no bucket starts on this date.')
        cells.append(dict(date=day.isoformat(), day=day.day, muted=(day.year,day.month) != (today.year,today.month),
                          entries=es, highlighted=touched, active=active_day, today=day==today,
                          detail='\n\n'.join(descriptions)))
    return local(now).strftime('%B %Y'), cells
