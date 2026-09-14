"""One presentation projection for all monitors. Calculations stay in the engine."""
from datetime import datetime
import math
from .engine import number, index, whole, countdown, month_cells, pacing, WEEK



def reset_duration(seconds):
    if seconds is None or seconds <= 0:
        return '—'
    if seconds < 60:
        return '<1m'
    minutes = int(seconds // 60)
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    return (f'{days}d ' if days else '') + f'{hours}h {minutes:02d}m'


def countdown_fields(start, end, now):
    active = index(start, end, now) if all(type(t) in (int, float) and math.isfinite(t) for t in (start, end, now)) else None
    if active is None:
        return dict(bucketSeconds=None, weeklySeconds=None, bucketFill=None,
                    weeklyResetFill=None, weeklyCountdown='—')
    bucket_seconds = start + (active + 1) * (WEEK // 7) - now
    weekly_seconds = end - now
    return dict(bucketSeconds=bucket_seconds, weeklySeconds=weekly_seconds,
                bucketFill=max(0, min(1, bucket_seconds / 86400)),
                weeklyResetFill=max(0, min(1, weekly_seconds / WEEK)),
                weeklyCountdown=reset_duration(weekly_seconds))

def project(store, now, interval=300, error=''):
    reading = store.get('reading')
    empty = dict(available='—', daily='—', weekly='—', plan='—', used='—', days='—',
                 countdown='—', credits='—', dailyFill=0, dailyKnown=False, weeklyFill=0, cells=[], month='',
                 status=error or 'Reading Codex quota…', note='', detail='', valid=False,
                 usedEstimated=False, hasEstimates=False, planBasis='', usedBasis='',
                 bucketSeconds=None, weeklySeconds=None, bucketFill=None,
                 weeklyResetFill=None, weeklyCountdown='—')
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
    records = store.records(reading, now)
    estimate = None
    if i is not None and not store.get('pending'):
        b, records, estimate = pacing(number(reading['remaining']), i, records)
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
    notes = []
    if b['plan'] == 0:
        notes.append('No quota available')
    if reading.get('short'):
        notes.append('Shorter quota window exhausted')
    if reading.get('correction') or (b['used'] is not None and b['used'] < 0) or (not estimate['fallback'] and b['ratio'] is not None and b['ratio'] > 100):
        notes.append('Provider balance correction')
    daily = whole(b['ratio'])
    weekly = whole(r)
    local_time = lambda timestamp: datetime.fromtimestamp(timestamp).astimezone().strftime('%a %d %b %Y %H:%M %Z') if timestamp is not None else 'unknown'
    detail = (f"{reading['bucket']} · {reading['provenance']}\n{record['quality']}\n"
              f"Baseline: {local_time(record['baseline'])}\nWeekly deadline: {local_time(reading['end'])}\n"
              f"{reading['precision']}; measurement rounding unspecified.\n"
              f"{record['planBasis']}\n{record['usedBasis']}")
    if estimate['diagnostic']:
        detail += '\n' + estimate['diagnostic']
    if b['debt']:
        detail += '\nEstimated over-plan: '+whole(b['debt'])+' weekly points'
    if record['net'] is not None and record['net'] < 0:
        detail += '\nNet correction: '+whole(-record['net'])+' weekly points returned'
    return dict(available=whole(b['available']), daily=daily, weekly=weekly, plan=whole(b['plan']),
                used=whole(record['used']), days=str(6-i),
                countdown=countdown(reading['start']+(i+1)*WEEK//7-now),
                credits=whole(reading['credits']), dailyKnown=b['ratio'] is not None, dailyFill=min(100,max(0,int(daily))) if daily != '—' else 0,
                weeklyFill=int(weekly), cells=cells, month=month, status=status,
                note=' · '.join(notes), detail=detail, valid=True,
                usedEstimated=record['usedEstimated'], hasEstimates=any(x['usedEstimated'] for x in records),
                planBasis=record['planBasis'], usedBasis=record['usedBasis'],
                basis='standard' if estimate['fallback'] else 'opening',
                estimateResidual=estimate['residual'], estimateDiagnostic=estimate['diagnostic'],
                **countdown_fields(reading['start'], reading['end'], now))
