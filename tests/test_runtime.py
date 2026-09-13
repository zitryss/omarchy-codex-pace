"""Integration checks with a fake executable on PATH and an isolated XDG state directory."""
import json
import os
from pathlib import Path
import select
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.marker=self.root/'starts'
        stub=self.root/'codex'
        stub.write_text('#!'+sys.executable+'\nimport os, runpy, sys\n'
                        'with open(os.environ["PACE_TEST_STARTS"],"a") as f: f.write(str(os.getpid())+"\\n")\n'
                        'sys.argv=[sys.argv[0], os.environ.get("PACE_TEST_MODE","normal")]\n'
                        'runpy.run_path('+repr(str(ROOT/'tests/fake_server.py'))+',run_name="__main__")\n')
        stub.chmod(0o700)
        self.env=dict(os.environ,PATH=str(self.root)+os.pathsep+os.environ['PATH'],
                      XDG_STATE_HOME=str(self.root/'state'),PACE_TEST_STARTS=str(self.marker),
                      PACE_TEST_RESET=str(int(time.time())+500000),PYTHONDONTWRITEBYTECODE='1')
        self.children=[]
    def tearDown(self):
        for p in self.children:
            if p.poll() is None:
                p.terminate()
                try: p.wait(timeout=3)
                except subprocess.TimeoutExpired: p.kill(); p.wait()
            p.stdin.close(); p.stdout.close(); p.stderr.close()
        self.temp.cleanup()
    def launch(self):
        p=subprocess.Popen([sys.executable,'-B',str(ROOT/'pace.py'),'watch'],env=self.env,
                           stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.children.append(p)
        return p
    def view(self,p,predicate=lambda v: v.get('valid')):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            ready,_,_=select.select([p.stdout],[],[],.2)
            if ready:
                raw=p.stdout.readline()
                if not raw: self.fail('Bridge exited: '+p.stderr.read().decode())
                view=json.loads(raw)
                if predicate(view): return view
        self.fail('Timed out awaiting test view')
    def test_reload_deduplication_and_frozen_baseline(self):
        first=self.launch(); initial=self.view(first)
        second=self.launch()
        first.stdin.close(); first.wait(timeout=3)
        second_view=self.view(second)
        self.assertEqual(initial['plan'],second_view['plan'])
        self.assertEqual(len(self.marker.read_text().splitlines()),1)
        # A fresh panel opening cannot cause another server launch.
        second.stdin.write(b'refresh\n'); second.stdin.flush()
        self.view(second)
        self.assertEqual(len(self.marker.read_text().splitlines()),1)
    def test_backoff_and_retry_guidance_survive_restart(self):
        self.env['PACE_TEST_MODE']='error'
        first=self.launch()
        self.view(first,lambda v:'request failed' in v['status'])
        database=self.root/'state/omarchy/codex-pace/ledger.sqlite3'
        with sqlite3.connect(database) as db:
            retry=json.loads(db.execute("SELECT value FROM meta WHERE key='retry'").fetchone()[0])
        self.assertGreater(retry['due'],time.time()+85)
        first.stdin.close(); first.wait(timeout=3)
        second=self.launch()
        second.stdin.write(b'refresh\n'); second.stdin.flush()
        self.view(second,lambda v:'request failed' in v['status'])
        self.assertEqual(len(self.marker.read_text().splitlines()),1)
    def test_termination_reaps_owned_inflight_server(self):
        self.env['PACE_TEST_MODE']='timeout'
        first=self.launch()
        deadline=time.monotonic()+3
        while not self.marker.exists() and time.monotonic()<deadline: time.sleep(.02)
        pid=int(self.marker.read_text().strip())
        first.terminate(); first.wait(timeout=3)
        with self.assertRaises(ProcessLookupError): os.kill(pid,0)
    def test_config_limits(self):
        for args in (['--interval','0'],['--interval','3601'],['--retention','1'],['--bucket','']):
            result=subprocess.run([sys.executable,'-B',str(ROOT/'pace.py'),'configure',*args],env=self.env,capture_output=True)
            self.assertNotEqual(result.returncode,0)
        self.assertFalse(self.marker.exists())

    def test_resume_gap_requests_fresh_reading(self):
        process=self.launch()
        self.view(process)
        process.send_signal(signal.SIGSTOP)
        try:
            time.sleep(5.2)  # Simulates a suspended helper, not a suspended desktop.
        finally:
            process.send_signal(signal.SIGCONT)
        self.view(process)
        deadline=time.monotonic()+3
        while len(self.marker.read_text().splitlines()) < 2 and time.monotonic()<deadline:
            time.sleep(.05)
        self.assertEqual(len(self.marker.read_text().splitlines()),2)
