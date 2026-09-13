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
    interval = data.get('interval',300)
    if interval == 60 and not data.get('intervalExplicit', False):
        interval = 300  # Migrate the original saved default, preserving explicit choices.
    retention = data.get('retention',90)
    bucket = data.get('bucket')
    if type(interval) is not int or not 30 <= interval <= 3600 or type(retention) is not int or not 7 <= retention <= 365:
        raise Unavailable('Invalid settings: interval 30–3600, retention 7–365')
    if bucket is not None and (not isinstance(bucket,str) or not bucket or len(bucket)>200):
        raise Unavailable('Invalid selected bucket')
    return dict(interval=interval,retention=retention,bucket=bucket,
                intervalExplicit=data.get('intervalExplicit', interval != 300), settingsVersion=2)


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
    manual = False
    task = None
    input_buffer = b''
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig,stop.set)
    def input_ready():
        nonlocal manual, input_buffer
        data = os.read(sys.stdin.fileno(),4096)
        if not data:
            stop.set()
            loop.remove_reader(sys.stdin.fileno())
        else:
            input_buffer = (input_buffer + data)[-8192:]
            while b'\n' in input_buffer:
                command, input_buffer = input_buffer.split(b'\n', 1)
                if task is None and command in (b'refresh', b'stale'):
                    manual = manual or command == b'refresh'
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
    due = (last_reading['at'] + settings(root)['interval']) if last_reading else 0
    if retry.get('failures', 0):
        due = max(due, retry.get('due', 0))
    retry_until = retry.get('retry_until', retry.get('due', 0) if retry.get('failures', 0) else 0)
    boundary_handled = None
    failures = retry.get('failures', 0)
    last_tick = time.time()
    error = retry.get('error', '')
    try:
        while not stop.is_set():
            now = time.time()
            config = settings(root)
            reading = store.get('reading')
            if not failures and (now-last_tick > 5 or now < last_tick) and (not reading or now-reading['at'] >= config['interval']):
                due = min(due, now)
            last_tick = now
            # Refresh once on crossing a virtual boundary, including the provider deadline.
            if reading:
                from pace.engine import index
                previous = index(reading['start'], reading['end'], reading['at'])
                boundary = reading['start'] + (previous + 1) * (reading['end']-reading['start'])/7 if previous is not None else reading['end']
                identity = (reading['epoch'], boundary) if 'epoch' in reading else (reading['account'], reading['bucket'], boundary)
                if now >= boundary and identity != boundary_handled:
                    boundary_handled = identity
                    if not failures:
                        due = min(due, now)
            if wake.is_set():
                wake.clear()
                reading = store.get('reading')
                if manual or (not failures and (not reading or now-reading['at'] >= config['interval'])):
                    due = min(due,now)
                manual = False
            if task and task.done():
                try:
                    reading = task.result()
                    store.accept(reading,config['interval'],config['retention'])
                    failures,error = 0,''
                    retry_until = 0
                    due = now+config['interval']
                except Unavailable as exc:
                    failures += 1
                    error = str(exc)
                    retry_until = now + exc.retry
                    due = now+max(exc.retry,min(3600,config['interval']*2**min(failures-1,6)))
                except Exception:
                    failures += 1
                    error = 'Collector or state unavailable'
                    due = now+min(3600,config['interval']*2**min(failures-1,6))
                with store.db:
                    store.put('retry', dict(due=due, failures=failures, error=error, retry_until=retry_until))
                task = None
            if task is None and now >= max(due, retry_until):
                selected = config['bucket']
                # A remembered selection is safe only after observing the current account.
                # Explicit config is required for ambiguity; single returned buckets self-select.
                task = asyncio.create_task(collect(selected))
            view = project(store,now,config['interval'],error)
            view['pending'] = task is not None
            print(json.dumps(view,separators=(',',':')),flush=True)
            try:
                await asyncio.wait_for(wake.wait(),1)
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
        if args.interval is not None:
            config['intervalExplicit'] = True
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
