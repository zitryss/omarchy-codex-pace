"""Standard-plan defaults and provisional residual allocation; no provider access."""
from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest
from pace.engine import BASE, WEEK, pacing, whole
from pace.store import Store
from pace.view import project
from test_store import reading


def unknown():
    return [dict(plan=None, opening=None, used=None) for _ in range(7)]


class DefaultTests(unittest.TestCase):
    def test_exact_requested_fallbacks(self):
        for remaining,available,ratio,used in ((86,F(102,7),102,0),(90,F(130,7),130,0),(80,F(60,7),60,F(40,7))):
            b, records, info = pacing(F(remaining),1,unknown())
            self.assertEqual(b['available'],available)
            self.assertEqual(b['plan'],BASE)
            self.assertEqual(b['ratio'],ratio)
            self.assertEqual(b['used'],used)
            self.assertEqual(whole(b['used']),'5' if remaining==80 else '0')
            self.assertTrue(records[1]['usedEstimated'])
            self.assertEqual(records[0]['used'],100-remaining-used)
            self.assertTrue(records[0]['usedEstimated'])
            self.assertTrue(all(r['used'] is None for r in records[2:]))
            self.assertTrue(all(r['plan']==BASE for r in records))
            self.assertEqual(info['diagnostic'],'')
        b,_,_=pacing(F(600,7),1,unknown())
        self.assertEqual(b['available'],BASE)
        self.assertEqual(b['ratio'],100)

    def test_fallback_and_opening_modes_differ_deliberately(self):
        for remaining in (86,90,80):
            records=unknown()
            records[1].update(opening=F(remaining),plan=F(remaining)-F(500,7),used=F(0))
            b,result,info=pacing(F(remaining),1,records)
            self.assertFalse(info['fallback'])
            self.assertEqual(b['ratio'],100)
            self.assertEqual(b['plan'],F(remaining)-F(500,7))
            self.assertFalse(result[1]['usedEstimated'])
            self.assertEqual(b['available'],b['plan'])

    def test_residual_preserves_measured_records_and_full_precision(self):
        records=unknown()
        records[0].update(plan=F(16),opening=F(100),used=F('4.5'))
        records[3].update(plan=F(10),opening=F(68),used=F(3))
        b,result,info=pacing(F(65),3,records)
        self.assertEqual(result[0]['used'],F('4.5'))
        self.assertEqual(result[0]['plan'],16)
        self.assertFalse(result[0]['usedEstimated'])
        self.assertEqual(result[1]['used'],F('13.75'))
        self.assertEqual(result[2]['used'],F('13.75'))
        self.assertEqual(sum(r['used'] for r in result[:4]),35)
        self.assertNotEqual(sum(int(whole(r['used'])) for r in result[:4]),35)
        self.assertIsNone(records[1]['used'])  # Pure projection, never mutates evidence.
        self.assertTrue(all(r['used'] is None for r in result[4:]))

    def test_inconsistent_and_negative_usage_does_not_force_history(self):
        for measured,current_balance in ((F(50),F(90)),(F(-1),F(80))):
            records=unknown(); records[0].update(plan=BASE,opening=F(100),used=measured)
            _,result,info=pacing(current_balance,2,records)
            self.assertEqual(result[0]['used'],measured)
            self.assertIsNone(result[1]['used'])
            self.assertFalse(result[1]['usedEstimated'])
            self.assertTrue(info['diagnostic'])
        records=unknown();records[2].update(opening=F(70),plan=F(90,7),used=F(-1))
        _,result,info=pacing(F(71),2,records)
        self.assertEqual(result[2]['used'],-1)
        self.assertIsNone(result[0]['used'])
        self.assertIn('corrections',info['diagnostic'])

    def test_no_eligible_history_retains_discrepancy(self):
        b,records,info=pacing(F(0),0,unknown())
        self.assertEqual(b['used'],BASE)
        self.assertTrue(info['diagnostic'])
        self.assertEqual(F(info['residual']),100-BASE)
        self.assertTrue(all(r['used'] is None for r in records[1:]))

    def test_zero_measured_plan_does_not_become_fallback(self):
        records=unknown();records[1].update(opening=F(60),plan=F(0),used=F(0))
        b,projected,info=pacing(F(60),1,records)
        self.assertFalse(info['fallback'])
        self.assertEqual(b['plan'],0)
        self.assertIsNone(b['ratio'])
        self.assertFalse(projected[1]['usedEstimated'])

    def test_projection_snapshot_is_not_changed_or_promoted(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger';store=Store(path)
            store.accept(reading(86500,'86',source_at=None,timing_quality='receipt timestamp'))
            before=list(store.db.iterdump())
            v=project(store,86500)
            self.assertEqual((v['available'],v['plan'],v['daily'],v['used']),('14','14','102','0'))
            self.assertEqual((v['dailyFill'],v['weeklyFill']),(100,86))
            self.assertTrue(v['usedEstimated'])
            self.assertEqual(v['basis'],'standard')
            self.assertNotIn('correction',v['note'])
            self.assertEqual(list(store.db.iterdump()),before)
            entries=[e for c in v['cells'] for e in c['entries']]
            self.assertEqual(len(entries),7)
            self.assertEqual((entries[0]['used'],entries[1]['used']),('14','0'))
            self.assertTrue(all(e['plan']=='14' for e in entries))
            self.assertTrue(entries[0]['usedEstimated'])
            self.assertIn('Not reconstructed',entries[0]['detail'])
            store.accept(reading(86800,'85',source_at=None,timing_quality='receipt timestamp'))
            later=project(store,86800)
            self.assertEqual(later['basis'],'standard')
            self.assertEqual(later['plan'],'14')
            self.assertEqual(later['daily'],'95')
            self.assertTrue(later['usedEstimated'])
            self.assertTrue(all(r['opening'] is None for r in store.records(store.get('reading'))))
            store.db.close(); store=Store(path)
            self.assertEqual(project(store,86800),later)
            store.db.close()

    def test_genuine_opening_evidence_takes_precedence(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'ledger')
            store.accept(reading(86401,'86',source_at=None,timing_quality='receipt timestamp'))
            self.assertEqual(project(store,86401)['basis'],'standard')
            # Synthetic delayed evidence has a verified source timestamp at the boundary.
            store.accept(reading(86402,'88',source_at=86400))
            store.accept(reading(86403,'86',source_at=86403))
            v=project(store,86403)
            self.assertEqual((v['basis'],v['plan'],v['used'],v['daily']),('opening','16','2','87'))
            self.assertFalse(v['usedEstimated'])
            store.db.close()

    def test_resets_accounts_stale_and_missing_data(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'ledger')
            self.assertEqual(project(store,1)['daily'],'—')
            store.accept(reading(86500,'80',source_at=None,timing_quality='receipt timestamp'))
            self.assertIn('Stale',project(store,87100)['status'])
            self.assertEqual(project(store,WEEK)['daily'],'—')
            store.accept(reading(WEEK+1,'100',start=WEEK,end=2*WEEK,source_at=None,timing_quality='receipt timestamp'))
            view=project(store,WEEK+1)
            self.assertEqual((view['daily'],view['used']),('100','0'))
            self.assertEqual(view['estimateResidual'],'0')
            self.assertTrue(all(e['used']=='—' for c in view['cells'] for e in c['entries'] if e['id']>0))
            store.accept(reading(WEEK+2,'99',start=WEEK,end=2*WEEK,account='other',source_at=None,timing_quality='receipt timestamp'))
            self.assertEqual(project(store,WEEK+2)['daily'],'93')
            store.db.close()

    def test_fallback_correction_recomputes_estimates_not_measurements(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'ledger')
            store.accept(reading(86500,'80',source_at=None,timing_quality='receipt timestamp'))
            self.assertEqual(project(store,86500)['used'],'5')
            store.accept(reading(86510,'86',source_at=None,timing_quality='receipt timestamp'))
            v=project(store,86510)
            self.assertEqual((v['used'],v['daily']),('0','102'))
            self.assertTrue(v['usedEstimated'])
            self.assertEqual(v['basis'],'standard')
            self.assertIn('correction',v['note'])
            self.assertEqual(store.db.execute('SELECT sum(correction) FROM snapshots').fetchone()[0],1)
            self.assertIsNone(store.records(store.get('reading'))[1]['used'])
            store.db.close()
