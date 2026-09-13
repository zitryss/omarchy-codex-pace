"""Revision regressions: interval overlap and evidence, using synthetic dates/balances."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from fractions import Fraction as F
from pace.engine import WEEK, budget, whole, month_cells
from pace.store import Store
from pace.view import project
from pace.provider import Unavailable
from test_store import reading

BERLIN=ZoneInfo('Europe/Berlin')
START=int(datetime(2026,9,12,10,26,tzinfo=BERLIN).timestamp())
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bridge',ROOT/'pace.py')
bridge=importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)


class RevisionTests(unittest.TestCase):
    def test_screenshot_opening_vs_launch_evidence(self):
        for known in (False,True):
            with tempfile.TemporaryDirectory() as d:
                store=Store(Path(d)/'ledger')
                begin=START+86400
                at=begin if known else begin+9*3600+35*60
                store.accept(reading(at,'88',start=START,end=START+WEEK,
                    source_at=at if known else None,
                    timing_quality='source timestamp' if known else 'receipt timestamp'))
                # Preserve the original launch baseline as archival evidence.
                with store.db:
                    store.db.execute("UPDATE buckets SET opening='88',baseline_at=?,quality='Since tracking began' WHERE idx=1",(at,))
                now=begin+10*3600+23*60
                store.accept(reading(now,'87',start=START,end=START+WEEK,source_at=None,timing_quality='receipt timestamp'))
                view=project(store,now)
                self.assertEqual((view['available'],view['weekly'],view['days'],view['countdown']),('15','87','5','13h 37m'))
                self.assertEqual((view['plan'],view['daily'],view['used']),('16','93','1') if known else ('—','—','—'))
                self.assertNotIn('Since tracking began',json.dumps(view))
                self.assertEqual(store.db.execute('SELECT count(*) FROM snapshots').fetchone()[0],2)
                self.assertEqual(store.db.execute('SELECT opening FROM buckets WHERE idx=1').fetchone()[0],'88')
                store.db.close()

    def test_surplus_and_debt_open_at_hundred(self):
        for balance,plan in ((86,F(102,7)),(90,F(130,7)),(80,F(60,7))):
            b=budget(F(balance),1,F(balance))
            self.assertEqual(b['plan'],plan)
            self.assertEqual(whole(b['ratio']),'100')
            self.assertEqual(b['used'],0)

    def test_overlap_active_and_midnight_outline(self):
        def cells(now):
            return month_cells(START,START+WEEK,now,[{} for _ in range(7)],BERLIN)[1]
        before=datetime(2026,9,13,23,59,tzinfo=BERLIN).timestamp()
        for now,today in ((before,13),(before+60,14)):
            cs=cells(now)
            self.assertEqual([c['day'] for c in cs if c['highlighted']],list(range(12,20)))
            self.assertEqual([c['day'] for c in cs if c['active']],[13,14])
            self.assertEqual([c['day'] for c in cs if c['today']],[today])
            self.assertEqual(sum(len(c['entries']) for c in cs),7)
            endpoint=next(c for c in cs if c['date']=='2026-09-19')
            self.assertEqual(endpoint['entries'],[])

    def test_midnight_endpoint_and_dst_overlap(self):
        for date in ((2026,9,12),(2026,3,27),(2026,10,23),(2026,12,29)):
            start=datetime(*date,tzinfo=BERLIN).timestamp()
            end=start+WEEK
            _,cs=month_cells(start,end,start+86400,[{} for _ in range(7)],BERLIN)
            self.assertEqual(sum(len(c['entries']) for c in cs),7)
            for c in cs:
                midnight=datetime.fromisoformat(c['date']).replace(tzinfo=BERLIN)
                from datetime import timedelta
                following=midnight+timedelta(days=1)
                self.assertEqual(c['highlighted'],max(start,midnight.timestamp())<min(end,following.timestamp()))
            if datetime.fromtimestamp(end,BERLIN).hour==0:
                self.assertFalse(next(c for c in cs if c['date']==datetime.fromtimestamp(end,BERLIN).date().isoformat())['highlighted'])

    def test_receipt_at_boundary_is_not_source_timestamp(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'ledger')
            store.accept(reading(0,source_at=None,timing_quality='receipt timestamp'))
            self.assertEqual(project(store,0)['daily'],'—')
            self.assertIn('receipt timestamp',project(store,0)['detail'])
            store.db.close()

    def test_historical_use_requires_closing_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'ledger')
            store.accept(reading(0))
            store.accept(reading(86399,'90'))
            self.assertIsNone(store.records(store.get('reading'),86401)[0]['used'])
            store.accept(reading(86401,'89',source_at=86400))
            self.assertEqual(store.records(store.get('reading'))[0]['used'],11)
            self.assertEqual(store.records(store.get('reading'))[1]['opening'],89)
            with self.assertRaises(Unavailable): store.accept(reading(86402,'88',source_at=86399))
            store.db.close()

    def test_legacy_schema_migrates_without_history_loss(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger'
            with sqlite3.connect(path) as db:
                db.executescript('''CREATE TABLE snapshots(epoch INTEGER,at REAL,remaining TEXT,precision TEXT,correction INTEGER,PRIMARY KEY(epoch,at));
                INSERT INTO snapshots VALUES(1,100,'88','reported integer',0); PRAGMA user_version=1;''')
            store=Store(path)
            row=store.db.execute('SELECT remaining,timing_quality FROM snapshots').fetchone()
            self.assertEqual(row,('88','legacy receipt timestamp'))
            self.assertEqual(store.db.execute('PRAGMA user_version').fetchone()[0],2)
            store.db.close()

    def test_settings_default_migration_and_explicit_choices(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertEqual(bridge.settings(root)['interval'],300)
            for config,want in (({'interval':60},300),({'interval':60,'intervalExplicit':True},60),({'interval':120},120)):
                (root/'settings.json').write_text(json.dumps(dict(config,bucket='codex')))
                parsed=bridge.settings(root)
                self.assertEqual(parsed['interval'],want)
                self.assertEqual(parsed['bucket'],'codex')
