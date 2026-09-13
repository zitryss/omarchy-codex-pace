import asyncio
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from pace.provider import RPC, Unavailable, collect, select
from pace.engine import WEEK

SERVER=Path(__file__).with_name('fake_server.py')


def result(**kwargs):
    return dict(dict(accountId='fixture-account',rateLimits={},rateLimitsByLimitId={'codex':{
       'primary':{'windowDurationMins':10080,'usedPercent':12,'resetsAt':WEEK}}}),**kwargs)


class SelectionTests(unittest.TestCase):
    def test_primary_weekly_and_raw_percentage(self):
        v=select({'type':'chatgpt'},result(),None,1)
        self.assertEqual(v['remaining'],'88')
        self.assertEqual(v['start'],0)
        self.assertEqual(v['bucket'],'codex')
        self.assertNotEqual(v['account'],'fixture-account')

    def test_explicit_bucket_required(self):
        data=result()
        data['rateLimitsByLimitId']['other']=data['rateLimitsByLimitId']['codex']
        with self.assertRaises(Unavailable): select({'type':'chatgpt'},data,None,1)
        self.assertEqual(select({'type':'chatgpt'},data,'codex',1)['bucket'],'codex')
        with self.assertRaises(Unavailable): select({'type':'chatgpt'},data,'absent',1)

    def test_fallback(self):
        data=result()
        data['rateLimits']=dict(data['rateLimitsByLimitId']['codex'],limitId='fallback')
        data['rateLimitsByLimitId']=None
        self.assertEqual(select({'type':'chatgpt'},data,None,1)['bucket'],'fallback')

    def test_missing_identity_and_auth(self):
        with self.assertRaises(Unavailable): select({'type':'chatgpt'},result(accountId=None),None,1)
        for account in (None,{'type':'apiKey'}):
            with self.assertRaises(Unavailable): select(account,result(),None,1)

    def test_invalid_and_fractional(self):
        for value in (-1,101,True,None,'12',float('nan'),float('inf')):
            data=result(); data['rateLimitsByLimitId']['codex']['primary']['usedPercent']=value
            with self.assertRaises(Unavailable): select({'type':'chatgpt'},data,None,1)
        data=result(); data['rateLimitsByLimitId']['codex']['primary']['usedPercent']=12.5
        self.assertEqual(select({'type':'chatgpt'},data,None,1)['remaining'],'175/2')

    def test_bad_duration_reset_and_ambiguity(self):
        for change in ({'windowDurationMins':9999},{'resetsAt':None},{'resetsAt':True},{'resetsAt':WEEK+10},{'startsAt':100}):
            data=result(); data['rateLimitsByLimitId']['codex']['primary'].update(change)
            with self.assertRaises(Unavailable): select({'type':'chatgpt'},data,None,1)
        data=result(); data['rateLimitsByLimitId']['codex']['secondary']=data['rateLimitsByLimitId']['codex']['primary']
        with self.assertRaises(Unavailable): select({'type':'chatgpt'},data,None,1)

    def test_malformed_identity_and_summary(self):
        data=result()
        data['rateLimitsByLimitId']['codex']['limitId']='other'
        with self.assertRaises(Unavailable): select({'type':'chatgpt'},data,'codex',1)
        for summary in ([1], {'availableCount':-1}, {'availableCount':True}):
            with self.assertRaises(Unavailable): select({'type':'chatgpt'},result(rateLimitResetCredits=summary),None,1)

    def test_reset_credit_count_not_rows_or_money(self):
        for summary,want in [(None,None),({},None),({'availableCount':3,'credits':[]},3),({'availableCount':0,'credits':[{}]},0)]:
            data=result(rateLimitResetCredits=summary)
            data['rateLimitsByLimitId']['codex']['credits']={'balance':'500'}
            self.assertEqual(select({'type':'chatgpt'},data,None,1)['credits'],want)


class RpcTests(unittest.IsolatedAsyncioTestCase):
    async def test_handshake_notifications_and_out_of_order(self):
        v=await collect('codex',[sys.executable,str(SERVER),'normal'])
        self.assertEqual(v['remaining'],'99')
        self.assertIsNone(v['credits'])

    async def test_process_errors_timeout_and_cleanup(self):
        for mode in ('exit','timeout','invalid','oversize'):
            async with RPC([sys.executable,str(SERVER),mode],timeout=.1) as rpc:
                with self.assertRaises(Unavailable): await rpc.request('initialize')
            self.assertIsNotNone(rpc.proc.returncode)

    async def test_redacted_rpc_error_and_retry(self):
        async with RPC([sys.executable,str(SERVER),'error']) as rpc:
            with self.assertRaises(Unavailable) as caught: await rpc.request('initialize')
            self.assertEqual(caught.exception.retry,90)
            self.assertNotIn('secret',str(caught.exception))

    async def test_missing_executable(self):
        with self.assertRaises(Unavailable):
            async with RPC(['/definitely/not/a/command']): pass


class LockTests(unittest.TestCase):
    def test_no_duplicate_collectors(self):
        spec=importlib.util.spec_from_file_location('bridge',Path(__file__).parents[1]/'pace.py')
        bridge=importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)
        with tempfile.TemporaryDirectory() as temp:
            first=bridge.acquire(Path(temp))
            self.assertIsNotNone(first)
            self.assertIsNone(bridge.acquire(Path(temp)))
            first.close()
            replacement=bridge.acquire(Path(temp))
            self.assertIsNotNone(replacement)
            replacement.close()


if __name__=='__main__': unittest.main()
