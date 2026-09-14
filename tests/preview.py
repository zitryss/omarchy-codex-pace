#!/usr/bin/env python3
"""Synthetic UI fixtures, generated in temporary SQLite; never access the real ledger/provider."""
import json
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pace.engine import WEEK
from pace.store import Store
from pace.view import project


def fixture(name):
    if name not in ('normal','unknown','fallback','screenshot','debt','zero','correction','stale','expired','auth','year','dst','boundary','near-reset','empty','spent','long-error'):
        raise ValueError('Unknown fixture')
    start=int(datetime(2026,12,29 if name=='year' else 10,18,tzinfo=timezone.utc).timestamp())
    if name in ('unknown','fallback','screenshot'):
        start=int(datetime(2026,9,12,10,26,tzinfo=ZoneInfo('Europe/Berlin')).timestamp())
    if name=='dst':
        start=int(datetime(2026,3,27,18,tzinfo=timezone.utc).timestamp())
    def reading(at, r):
        return dict(account='synthetic',bucket='fixture',start=start,end=start+WEEK,at=at,
                    source_at=at if name not in ('unknown','fallback') else None, timing_quality='source timestamp' if name not in ('unknown','fallback') else 'receipt timestamp',remaining=r,credits=None,provenance='synthetic fixture',precision='reported integer',short=False)
    with tempfile.TemporaryDirectory(prefix='codex-pace-fixture-') as temp:
        store=Store(Path(temp)/'fixture.sqlite3')
        if name in ('auth','empty'):
            view=project(store,start,error='Run codex login with your existing subscription' if name=='auth' else '')
        else:
            now=start+86400
            opening='60' if name in ('debt','zero') else '88'
            store.accept(reading(now,opening))
            if name=='correction':
                now+=10; store.accept(reading(now,'95'))
            elif name not in ('debt','zero'):
                now+=10; store.accept(reading(now,'87' if name in ('unknown','fallback','screenshot') else '84'))
            if name in ('unknown','fallback','screenshot'):
                now=start+86400+10*3600+23*60
                store.accept(reading(now,'86' if name=='fallback' else '87'))
            if name=='stale': now+=601
            if name=='expired': now=start+WEEK
            if name=='boundary': now=start+2*86400
            if name=='near-reset': now=start+WEEK-30
            if name=='spent':
                now+=1; store.accept(reading(now,'0'))
            view=project(store,now,error=('Collector unavailable. Check the existing Codex CLI login and retry. ' * 15) if name=='long-error' else '')
        view['fixture']=name
        store.db.close()
        return view


if __name__=='__main__':
    print(json.dumps(fixture(sys.argv[1])))
