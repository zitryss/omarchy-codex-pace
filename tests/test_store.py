import tempfile
import unittest
from pathlib import Path
from fractions import Fraction as F
from pace.engine import WEEK
from pace.store import Store
from pace.provider import Unavailable
from pace.view import project


def reading(at=0,remaining='100',**kwargs):
    return dict(dict(account='test-account',bucket='test-bucket',start=0,end=WEEK,
       at=at,source_at=at,timing_quality='source timestamp',remaining=remaining,credits=None,provenance='test inferred',precision='reported integer',short=False),**kwargs)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'ledger.sqlite3'
        self.store=Store(self.path)
    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()
    def add(self,*args,**kwargs):
        return self.store.accept(reading(*args,**kwargs))

    def test_persist_frozen_plan(self):
        self.add(0)
        self.add(10,'99')
        self.store.db.close()
        self.store=Store(self.path)
        v=project(self.store,10)
        self.assertEqual((v['plan'],v['daily'],v['used']),('14','93','1'))
        self.assertEqual(self.store.db.execute('PRAGMA user_version').fetchone()[0],2)

    def test_repeated_readings_and_corrections_telescope(self):
        self.add(0)
        for at,r in [(10,'99'),(20,'99'),(30,'98'),(40,'99')]: self.add(at,r)
        records=self.store.records(self.store.get('reading'))
        self.assertEqual(records[0]['used'],1)
        self.assertEqual(records[0]['plan'],F(100,7))
        self.assertEqual(self.store.db.execute('SELECT sum(correction) FROM snapshots').fetchone()[0],1)
        self.assertIn('correction',project(self.store,40)['note'])

    def test_above_hundred_ratio_visual_only_clamped(self):
        self.add(0,'99')
        self.add(10,'100')
        v=project(self.store,10)
        self.assertEqual(v['daily'],'107')
        self.assertEqual(v['dailyFill'],100)
        self.assertEqual(v['used'],'—')
        self.assertIn('Net correction',v['detail'])

    def test_mid_bucket_first_run(self):
        self.add(86420,'88')
        self.add(86430,'84')
        v=project(self.store,86430)
        self.assertEqual((v['plan'],v['available'],v['daily'],v['used']),('14','12','88','1'))
        self.assertEqual(v['note'],'')
        self.assertIn('opening balance unavailable',v['detail'])
        self.assertEqual(self.store.records(self.store.get('reading'))[0]['plan'],None)

    def test_boundary_close_readings_do_not_prove_opening(self):
        self.add(86380,'88')
        self.add(86420,'87')
        rec=self.store.records(self.store.get('reading'))[1]
        self.assertIsNone(rec['opening'])
        self.assertIn('unavailable',rec['quality'])
        self.assertIsNone(rec['used'])

    def test_boundary_gap_not_assigned(self):
        self.add(100,'98')
        self.add(86400*3+100,'80')
        records=self.store.records(self.store.get('reading'))
        self.assertIsNone(records[1]['used'])
        self.assertIsNone(records[2]['used'])
        self.assertIsNone(records[3]['used'])
        self.assertIsNone(records[3]['net'])
        self.assertIn('unavailable',records[3]['quality'])

    def test_no_synthetic_offline_boundary_opening(self):
        self.add(86300,'88')
        v=project(self.store,86400)
        self.assertEqual(v['days'],'5')
        self.assertEqual(v['countdown'],'24h 00m')
        self.assertEqual(v['plan'],'14')
        self.assertEqual(v['daily'],'116')
        self.assertEqual(v['available'],'16')

    def test_out_of_order_is_rejected(self):
        self.add(50,'99')
        for t in (49,50):
            with self.assertRaises(Unavailable): self.add(t,'50')
        self.assertEqual(self.store.get('reading')['remaining'],'99')

    def test_stale_and_offline_reset(self):
        self.add(0)
        self.assertNotIn('Stale',project(self.store,599)['status'])
        self.assertIn('Stale',project(self.store,600)['status'])
        v=project(self.store,WEEK)
        self.assertFalse(v['valid'])
        self.assertEqual(v['countdown'],'—')
        self.assertEqual(v['days'],'—')
        self.assertIn('pending refresh',v['status'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM snapshots').fetchone()[0],1)

    def test_reset_carryover_expires(self):
        self.add(WEEK-10,'80')
        self.add(WEEK,'100',start=WEEK,end=2*WEEK)
        v=project(self.store,WEEK)
        self.assertEqual((v['plan'],v['available'],v['daily']),('14','14','100'))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM buckets').fetchone()[0],14)
        self.assertIsNone(self.store.db.execute('SELECT opening FROM buckets WHERE epoch=1 AND idx=0').fetchone()[0])

    def test_early_reset_requires_confirmation(self):
        self.add(100,'90')
        early=reading(200,'100',start=-1000,end=WEEK-1000)
        with self.assertRaises(Unavailable): self.store.accept(early)
        self.assertFalse(project(self.store,201)['valid'])
        self.assertEqual(self.store.get('reading')['remaining'],'90')
        self.store.accept(dict(early,at=260))
        self.assertNotEqual(self.store.get('reading')['epoch'],1)
        self.assertIsNone(self.store.records(self.store.get('reading'))[0]['opening'])

    def test_archived_window_cannot_be_reactivated_after_reset(self):
        self.add(100,'90')
        early=reading(200,'100',start=-1000,end=WEEK-1000)
        with self.assertRaises(Unavailable): self.store.accept(early)
        new=self.store.accept(dict(early,at=260))
        for at in (320,380):
            with self.assertRaises(Unavailable): self.add(at,'95')
        self.assertEqual(self.store.get('reading')['epoch'],new['epoch'])
        self.assertIsNone(self.store.records(self.store.get('reading'))[0]['opening'])

    def test_accounts_and_buckets_never_merge(self):
        self.add(0,'50')
        self.add(10,'100',account='new-account')
        self.add(20,'99',bucket='different-bucket')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM epochs').fetchone()[0],3)
        self.assertIsNone(self.store.records(self.store.get('reading'))[0]['opening'])

    def test_two_independent_progress_values(self):
        self.add(0)
        self.add(10,'99')
        v=project(self.store,10)
        self.assertEqual(v['dailyFill'],93)
        self.assertEqual(v['weeklyFill'],99)

    def test_credits_unavailable_and_zero(self):
        self.add(0)
        self.assertEqual(project(self.store,0)['credits'],'—')
        self.add(1,credits=0)
        self.assertEqual(project(self.store,1)['credits'],'0')

    def test_retention_removes_archived_state(self):
        self.add(0)
        self.add(100*86400,'100',start=100*86400,end=100*86400+WEEK)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM epochs').fetchone()[0],1)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM buckets').fetchone()[0],7)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM snapshots').fetchone()[0],1)

    def test_unknown_schema_not_overwritten(self):
        self.store.db.execute('PRAGMA user_version=3')
        with self.assertRaises(Unavailable): Store(self.path)


if __name__=='__main__': unittest.main()
