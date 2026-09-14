"""Four-bar projection regressions; deadline arithmetic is independent of civil dates."""
import unittest
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from pace.engine import WEEK
from pace.view import project, countdown_fields, reset_duration
from pace.store import Store
from test_store import reading


class PresentationTests(unittest.TestCase):
    def test_duration_formats(self):
        for seconds,expected in [(WEEK,'7d 0h 00m'),(86400,'1d 0h 00m'),(86399,'23h 59m'),
                                 (3600,'1h 00m'),(60,'0h 01m'),(59,'<1m'),(0,'—'),(None,'—')]:
            self.assertEqual(reset_duration(seconds),expected)

    def test_all_boundaries_and_independent_fills(self):
        for i in range(7):
            start=countdown_fields(0,WEEK,i*86400)
            self.assertEqual(start['bucketFill'],1)
            self.assertEqual(start['weeklyResetFill'],(7-i)/7)
            self.assertEqual(start['weeklySeconds'],(7-i)*86400)
            later=countdown_fields(0,WEEK,i*86400+3600)
            self.assertAlmostEqual(later['bucketFill'],23/24)
            self.assertLess(later['weeklyResetFill'],start['weeklyResetFill'])
            self.assertEqual(later['weeklySeconds'],later['bucketSeconds']+(6-i)*86400)
        for remaining in (86400,3600,60,1):
            result=countdown_fields(0,WEEK,WEEK-remaining)
            self.assertEqual(result['bucketFill'],remaining/86400)
            self.assertEqual(result['weeklyResetFill'],remaining/WEEK)
        self.assertEqual(countdown_fields(0,WEEK,86400-1)['bucketSeconds'],1)
        self.assertEqual(countdown_fields(0,WEEK,86400)['bucketSeconds'],86400)

    def test_unverified_expired_and_missing_are_unknown(self):
        for start,end,now in ((0,WEEK,WEEK),(0,WEEK,-1),(0,WEEK-1,10),(None,None,10),(0,WEEK,float('nan'))):
            data=countdown_fields(start,end,now)
            self.assertIsNone(data['bucketFill'])
            self.assertIsNone(data['weeklyResetFill'])
            self.assertEqual(data['weeklyCountdown'],'—')
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'ledger')
            self.assertIsNone(project(store,0)['bucketFill'])
            store.accept(reading(0))
            with store.db: store.put('pending',{'signature':['test']})
            self.assertIsNone(project(store,10)['weeklyResetFill'])
            self.assertEqual(project(store,10)['daily'],'—')
            store.db.close()

    def test_dst_uses_elapsed_hours(self):
        for date in ((2026,3,28),(2026,10,24)):
            start=datetime(*date,12,tzinfo=ZoneInfo('Europe/Berlin')).timestamp()
            half=countdown_fields(start,start+WEEK,start+43200)
            self.assertEqual(half['bucketFill'],.5)
            self.assertEqual(half['weeklySeconds'],WEEK-43200)

    def test_local_ticks_preserve_history_and_quota_fill(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'ledger')
            store.accept(reading(86401,'90',source_at=None,timing_quality='receipt timestamp'))
            before=list(store.db.iterdump())
            a=project(store,86401);b=project(store,87001)
            self.assertEqual(a['daily'],'130')
            self.assertEqual(a['dailyFill'],100)
            self.assertEqual(a['weeklyFill'],90)
            self.assertGreater(a['bucketFill'],b['bucketFill'])
            self.assertGreater(a['weeklyResetFill'],b['weeklyResetFill'])
            self.assertIn('Stale',b['status'])
            self.assertEqual(before,list(store.db.iterdump()))
            store.db.close()
