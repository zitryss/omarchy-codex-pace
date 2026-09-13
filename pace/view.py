"""One presentation projection for all monitors. Calculations stay in the engine."""
from datetime import datetime
from .engine import number, index, budget, whole, countdown, month_cells, WEEK


def project(store, now, interval=60, error=''):
    reading = store.get('reading')
    empty = dict(available='—', daily='—', weekly='—', plan='—', observed='—', days='—',
                 countdown='—', credits='—', dailyFill=0, weeklyFill=0, cells=[], month='',
                 status=error or 'Reading Codex quota…', note='', detail='', valid=False)
    if not reading:
        return empty
    age = now-reading['at']
    stale = age < 0 or age >= 2*interval
    elapsed = max(0, int(age))
    age_text = (str(elapsed)+'s' if elapsed < 60 else str(elapsed//60)+'m' if elapsed < 3600 else str(elapsed//3600)+'h' if elapsed < 86400 else str(elapsed//86400)+'d')
    status = ('Stale · ' if stale else '') + 'Updated ' + age_text + ' ago'
    if error:
        status = error + ' · ' + status
    i = index(reading['start'],reading['end'],now)
    records = store.records(reading)
    month, cells = month_cells(reading['start'],reading['end'],now,records)
    empty.update(status=status, cells=cells, month=month, credits=whole(reading['credits']))
    if i is None:
        empty['status'] = 'Weekly reset pending refresh · '+status
        return empty
    if store.get('pending'):
        empty['status'] = 'Changed weekly window: verifying provider reset · ' + status
        return empty
    r = number(reading['remaining'])
    record = records[i]
    b = budget(r,i,record['opening'])
    notes = []
    if b['plan'] == 0:
        notes.append('No allowance available')
    if record['quality'] == 'Since tracking began':
        notes.append('Since tracking began')
    if reading.get('short'):
        notes.append('Shorter quota window exhausted')
    if reading.get('correction') or (b['observed'] is not None and b['observed'] < 0) or (b['ratio'] is not None and b['ratio'] > 100):
        notes.append('Provider balance correction')
    daily = whole(b['ratio'])
    weekly = whole(r)
    local_time = lambda timestamp: datetime.fromtimestamp(timestamp).astimezone().strftime('%a %d %b %Y %H:%M %Z') if timestamp is not None else 'unknown'
    detail = (f"{reading['bucket']} · {reading['provenance']}\n{record['quality']}\n"
              f"Baseline: {local_time(record['baseline'])}\nWeekly deadline: {local_time(reading['end'])}\n"
              f"{reading['precision']}; measurement rounding unspecified.\n"
              f"Observed is net change; gaps are not assigned to later buckets.")
    if b['debt']:
        detail += '\nEstimated over-plan: '+whole(b['debt'])+' weekly points'
    if record['net'] is not None and record['net'] < 0:
        detail += '\nNet correction: '+whole(-record['net'])+' weekly points returned'
    return dict(available=whole(b['available']), daily=daily, weekly=weekly, plan=whole(b['plan']),
                observed=whole(record['observed']), days=str(6-i),
                countdown=countdown(reading['start']+(i+1)*WEEK//7-now),
                credits=whole(reading['credits']), dailyFill=min(100,max(0,int(daily))) if daily != '—' else 0,
                weeklyFill=int(weekly), cells=cells, month=month, status=status,
                note=' · '.join(notes), detail=detail, valid=True)
