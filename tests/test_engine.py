import math
import unittest
from datetime import datetime, timezone
from fractions import Fraction as F
from zoneinfo import ZoneInfo
from pace.engine import BASE, WEEK, budget, countdown, index, month_cells, number, whole


class EngineTests(unittest.TestCase):
    def test_equal_capacity(self):
        self.assertEqual(sum([BASE]*7),100)
        self.assertEqual(BASE,F(100,7))
        self.assertEqual([whole(BASE)]*7,['14']*7)
        for i in range(7):
            self.assertEqual(BASE*(i+1)+BASE*(6-i),100)

    def test_all_half_open_boundaries(self):
        for i in range(7):
            self.assertEqual(index(0,WEEK,i*86400),i)
            self.assertEqual(index(0,WEEK,(i+1)*86400-.001),i)
        for t in (-1,WEEK,WEEK+1):
            self.assertIsNone(index(0,WEEK,t))
        self.assertIsNone(index(0,WEEK-1,100))

    def test_first_example(self):
        b=budget(F(99),0,F(100))
        self.assertEqual(b['available'],F(93,7))
        self.assertEqual(b['ratio'],93)
        self.assertEqual(b['used'],1)

    def test_second_example_ratio_before_floor(self):
        b=budget(F(84),1,F(88))
        self.assertEqual(b['plan'],F(116,7))
        self.assertEqual(b['available'],F(88,7))
        self.assertEqual([whole(b[k]) for k in ('plan','available','used','ratio')],['16','12','4','75'])
        self.assertNotEqual(b['ratio'],F(12,16)*100)
        first=budget(F(99),0,F(100))
        self.assertNotEqual(whole(first['ratio']),whole(F(int(whole(first['available'])),int(whole(first['plan'])))*100))

    def test_last_bucket(self):
        b=budget(F('7.81'),6,F(15))
        self.assertEqual(b['available'],F('7.81'))
        self.assertEqual(b['used'],F('7.19'))

    def test_zero_and_debt(self):
        b=budget(F(60),1,F(60))
        self.assertEqual(b['available'],0)
        self.assertEqual(b['plan'],0)
        self.assertIsNone(b['ratio'])
        self.assertEqual(b['debt'],F(80,7))
        # The same debt is only reflected in the remaining balance, once.
        self.assertEqual(budget(F(60),2,F(60))['available'],F(20,7))

    def test_small_positive_is_not_exhaustion(self):
        b=budget(F('85.8'),0,F(100))
        self.assertGreater(b['available'],0)
        self.assertEqual(whole(b['available']),'0')

    def test_fractional_snapshot_preserved(self):
        self.assertEqual(number(12.345),F(2469,200))
        self.assertEqual(budget(F('99.5'),0,F(100))['ratio'],F('96.5'))

    def test_unknown_and_correction(self):
        self.assertIsNone(budget(F(90),0)['ratio'])
        b=budget(F(100),0,F(99))
        self.assertGreater(b['ratio'],100)
        self.assertEqual(b['used'],-1)
        self.assertEqual(whole(b['used']),'—')

    def test_exact_floor_no_float_noise(self):
        for i in range(7):
            b=budget(F(100),i,F(100))
            self.assertEqual(whole(b['ratio']),'100')
        self.assertEqual(whole(F('99.999999999999999')),'99')
        self.assertEqual(whole(F(93,7)/F(100,7)*100),'93')
        self.assertEqual(whole(F('14.9999')),'14')
        self.assertEqual(whole(None),'—')

    def test_countdowns(self):
        for seconds,want in [(86400,'24h 00m'),(3600,'1h 00m'),(60,'0h 01m'),(59,'<1m'),(.001,'<1m'),(0,'—'),(-1,'—')]:
            self.assertEqual(countdown(seconds),want)
        for i in range(7):
            now=i*86400
            days=6-index(0,WEEK,now)
            self.assertEqual(days*86400+86400,WEEK-now)
            self.assertEqual(countdown((i+1)*86400-now),'24h 00m')

    def test_calendar_overlap_eight_dates_seven_entries(self):
        start=int(datetime(2026,9,10,18,tzinfo=timezone.utc).timestamp())
        records=[{} for _ in range(7)]
        _,cells=month_cells(start,start+WEEK,start,records,timezone.utc)
        marked=[c for c in cells if c['highlighted']]
        self.assertEqual([c['day'] for c in marked],[10,11,12,13,14,15,16,17])
        self.assertEqual(sum(len(c['entries']) for c in cells),7)
        self.assertEqual(marked[1]['entries'][0]['plan'],'14')
        self.assertEqual(marked[0]['entries'][0]['plan'],'—')
        self.assertEqual(datetime.fromisoformat(cells[0]['date']).weekday(),0)

    def test_year_month_and_dst(self):
        for date in [(2026,12,29),(2026,3,27),(2026,10,23),(2026,1,1)]:
            start=int(datetime(*date,18,tzinfo=timezone.utc).timestamp())
            for tz in (timezone.utc,ZoneInfo('Europe/Berlin'),ZoneInfo('America/New_York')):
                _,cells=month_cells(start,start+WEEK,start+3*86400,[{} for _ in range(7)],tz)
                ids=[e['id'] for c in cells for e in c['entries']]
                self.assertEqual(ids,list(range(7)))
                self.assertEqual(len(cells)%7,0)
        # Spring forward skips a civil date in Samoa; still exactly seven IDs.
        start=int(datetime(2011,12,28,10,tzinfo=timezone.utc).timestamp())
        _,cells=month_cells(start,start+WEEK,start,[{} for _ in range(7)],ZoneInfo('Pacific/Apia'))
        self.assertEqual(sum(len(c['entries']) for c in cells),7)

    def test_long_offline_gap_keeps_one_month(self):
        start=int(datetime(2025,1,1,tzinfo=timezone.utc).timestamp())
        now=int(datetime(2026,9,13,tzinfo=timezone.utc).timestamp())
        title,cells=month_cells(start,start+WEEK,now,[{} for _ in range(7)],timezone.utc)
        self.assertEqual(title,'September 2026')
        self.assertLessEqual(len(cells),42)
        self.assertFalse(any(c['highlighted'] for c in cells))

    def test_duplicate_civil_dates_preserve_entries(self):
        # Kwajalein moved back 23 hours in 1969; date labels are not IDs.
        start=int(datetime(1969,9,28,13,tzinfo=timezone.utc).timestamp())
        _,cells=month_cells(start,start+WEEK,start,[{} for _ in range(7)],ZoneInfo('Pacific/Kwajalein'))
        self.assertEqual(sum(len(c['entries']) for c in cells),7)
        self.assertTrue(any(len(c['entries'])==2 for c in cells))


if __name__=='__main__': unittest.main()
