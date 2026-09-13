#!/usr/bin/env python3
"""Native service bridge. One advisory lock serializes owned quota collectors across reloads."""
import argparse
import asyncio
import fcntl
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys
import time
from pace.provider import collect, Unavailable
from pace.store import Store
from pace.view import project


def state_root():
    root = Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'omarchy/codex-pace'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def settings(root):
    path = root/'settings.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    interval = data.get('interval',60)
    retention = data.get('retention',90)
    bucket = data.get('bucket')
    if type(interval) is not int or not 30 <= interval <= 3600 or type(retention) is not int or not 7 <= retention <= 365:
        raise Unavailable('Invalid settings: interval 30–3600, retention 7–365')
    if bucket is not None and (not isinstance(bucket,str) or not bucket or len(bucket)>200):
        raise Unavailable('Invalid selected bucket')
    return dict(interval=interval,retention=retention,bucket=bucket)


def acquire(root):
    lock = (root/'collector.lock').open('a')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        return None
    return lock


async def watch(root):
    stop = asyncio.Event()
    wake = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig,stop.set)
    def input_ready():
        data = os.read(sys.stdin.fileno(),4096)
        if not data:
            stop.set()
            loop.remove_reader(sys.stdin.fileno())
        elif b'refresh' in data:
            wake.set()
    loop.add_reader(sys.stdin.fileno(),input_ready)
    lock = None
    while not stop.is_set() and lock is None:
        lock = acquire(root)
        if lock is None:
            await asyncio.sleep(.2)
    if not lock:
        return
    store = Store(root/'ledger.sqlite3')
    task = None
    last_reading = store.get('reading')
    retry = store.get('retry', {})
    due = max(retry.get('due', 0), (last_reading['at'] + settings(root)['interval']) if last_reading else 0)
    failures = retry.get('failures', 0)
    last_tick = time.time()
    error = retry.get('error', '')
    try:
        while not stop.is_set():
            now = time.time()
            config = settings(root)
            if not failures and (now-last_tick > 5 or now < last_tick):
                due = min(due, now)  # Resume/clock change; one owned in-flight task remains deduplicated.
            last_tick = now
            if wake.is_set():
                wake.clear()
                reading = store.get('reading')
                if not failures and (not reading or now-reading['at'] >= config['interval']):
                    due = min(due,now)
            if task and task.done():
                try:
                    reading = task.result()
                    store.accept(reading,config['interval'],config['retention'])
                    failures,error = 0,''
                    due = now+config['interval']
                except Unavailable as exc:
                    failures += 1
                    error = str(exc)
                    due = now+max(exc.retry,min(3600,config['interval']*2**min(failures-1,6)))
                except Exception:
                    failures += 1
                    error = 'Collector or state unavailable'
                    due = now+min(3600,config['interval']*2**min(failures-1,6))
                with store.db:
                    store.put('retry', dict(due=due, failures=failures, error=error))
                task = None
            if task is None and now >= due:
                selected = config['bucket']
                # A remembered selection is safe only after observing the current account.
                # Explicit config is required for ambiguity; single returned buckets self-select.
                task = asyncio.create_task(collect(selected))
            print(json.dumps(project(store,now,config['interval'],error),separators=(',',':')),flush=True)
            try:
                await asyncio.wait_for(stop.wait(),1)
            except asyncio.TimeoutError:
                pass
    finally:
        if task:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        store.db.close()
        lock.close()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('watch')
    sub.add_parser('status')
    sub.add_parser('export')
    sub.add_parser('probe')
    cfg = sub.add_parser('configure')
    cfg.add_argument('--interval',type=int)
    cfg.add_argument('--retention',type=int)
    cfg.add_argument('--bucket')
    args = parser.parse_args()
    root = state_root()
    if args.action == 'configure':
        config = settings(root)
        for key in ('interval','retention','bucket'):
            if getattr(args,key) is not None:
                config[key] = getattr(args,key)
        temp = root/'settings.tmp'
        temp.write_text(json.dumps(config))
        # Validate before replacing the active config.
        if not 30 <= config['interval'] <= 3600 or not 7 <= config['retention'] <= 365 or (config['bucket'] is not None and not 0 < len(config['bucket']) <= 200):
            temp.unlink()
            parser.error('interval 30–3600; retention 7–365; nonempty bucket up to 200 characters')
        temp.replace(root/'settings.json')
    elif args.action == 'watch':
        asyncio.run(watch(root))
    elif args.action == 'probe':
        # Read-only diagnostic; never print raw account IDs or RPC responses.
        lock = acquire(root)
        if not lock:
            parser.error('Collector already running; use status')
        try:
            reading = asyncio.run(collect(settings(root)['bucket']))
            reading.pop('account',None)
            print(json.dumps(reading,indent=2))
        finally:
            lock.close()
    else:
        store = Store(root/'ledger.sqlite3')
        if args.action == 'status':
            print(json.dumps(project(store,time.time(),settings(root)['interval'],store.get('retry', {}).get('error','')),indent=2))
        else:
            print(json.dumps({table:[dict(zip([c[0] for c in cursor.description],row)) for row in cursor]
                for table in ('epochs','snapshots','buckets')
                for cursor in [store.db.execute('SELECT * FROM '+table)]},indent=2))
        store.db.close()


if __name__ == '__main__':
    try:
        main()
    except Unavailable as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, sqlite3.Error):
        print('Codex Pace unavailable; check CLI login, settings and state directory.',file=sys.stderr)
        sys.exit(1)
