"""Bounded, read-only app-server RPC. Credentials remain entirely inside Codex."""
import asyncio
import hashlib
import json
import math
import time
from .engine import WEEK, number


class Unavailable(Exception):
    def __init__(self, message, retry=0):
        super().__init__(message)
        self.retry = retry


class RPC:
    def __init__(self, command=None, timeout=20):
        self.command = command or ['codex', 'app-server']
        self.timeout = timeout
        self.serial = 0
        self.proc = None

    async def __aenter__(self):
        try:
            self.proc = await asyncio.create_subprocess_exec(*self.command, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=1024*1024)
        except OSError:
            raise Unavailable('Codex CLI unavailable in PATH') from None
        return self

    async def __aexit__(self, *args):
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), 2)
            except asyncio.TimeoutError:
                self.proc.kill()
                await self.proc.wait()

    async def send(self, message):
        self.proc.stdin.write((json.dumps(message)+'\n').encode())
        await self.proc.stdin.drain()

    async def request(self, method, params=None):
        self.serial += 1
        request_id = self.serial
        await self.send(dict(id=request_id, method=method, params=params or {}))
        async def receive():
            for _ in range(1000):
                raw = await self.proc.stdout.readline()
                if not raw:
                    raise Unavailable('Codex collector exited')
                try:
                    reply = json.loads(raw)
                except (ValueError, UnicodeError):
                    raise Unavailable('Invalid Codex RPC response') from None
                if not isinstance(reply, dict) or reply.get('id') != request_id:
                    continue  # Notifications and unrelated/out-of-order IDs cannot satisfy this call.
                if 'error' in reply:
                    data = (reply.get('error') or {}).get('data') or {}
                    retry = data.get('retryAfterSeconds', data.get('retry_after_seconds', None)) if isinstance(data, dict) else None
                    if retry is None and isinstance(data, dict):
                        milliseconds = data.get('retryAfterMs', 0)
                        retry = milliseconds / 1000 if type(milliseconds) in (int, float) else 0
                    retry = float(retry) if type(retry) in (int, float) and math.isfinite(retry) and retry >= 0 else 0
                    raise Unavailable('Codex quota request failed', retry)
                if not isinstance(reply.get('result'), dict):
                    raise Unavailable('Invalid Codex RPC result')
                return reply['result']
            raise Unavailable('Excessive Codex notifications')
        try:
            return await asyncio.wait_for(receive(), self.timeout)
        except (asyncio.TimeoutError, ValueError, BrokenPipeError, ConnectionError):
            raise Unavailable('Codex quota request timed out or disconnected') from None


def select(account, result, selected, now):
    if not isinstance(account, dict) or account.get('type') != 'chatgpt':
        raise Unavailable('Run codex login with your existing subscription')
    if not isinstance(result, dict):
        raise Unavailable('Invalid quota response')
    identity = result.get('accountId')
    if not isinstance(identity, str) or not identity:
        raise Unavailable('Account identity unavailable')
    buckets = result.get('rateLimitsByLimitId')
    if not buckets:
        single = result.get('rateLimits') or {}
        if not isinstance(single, dict):
            raise Unavailable('Invalid quota bucket')
        buckets = {single.get('limitId') or 'legacy': single}
    if not isinstance(buckets, dict):
        raise Unavailable('Invalid quota buckets')
    candidates = {}
    for key, bucket in buckets.items():
        if not isinstance(bucket, dict):
            continue
        windows = [w for w in (bucket.get('primary'), bucket.get('secondary'))
                   if isinstance(w, dict) and w.get('windowDurationMins') == 10080]
        if len(windows) == 1:
            candidates[key] = (windows[0], bucket)
    if selected:
        if selected not in candidates:
            raise Unavailable('Selected weekly quota bucket unavailable')
    elif len(candidates) == 1:
        selected = next(iter(candidates))
    else:
        raise Unavailable('Select a weekly bucket with pace.py configure --bucket ID')
    window, bucket = candidates[selected]
    if bucket.get('limitId') not in (None, selected):
        raise Unavailable('Ambiguous quota bucket identity')
    try:
        if type(window.get('usedPercent')) not in (int, float):
            raise ValueError()
        used = number(window['usedPercent'])
        end = window['resetsAt']
        if isinstance(end, bool) or not isinstance(end, int) or not 0 <= used <= 100 or not now < end <= now + WEEK:
            raise ValueError()
        start = end - WEEK
        provenance = 'inferred: resetsAt − verified 10080 minutes'
        if window.get('startsAt') is not None:
            if window['startsAt'] != start:
                raise ValueError()
            provenance = 'provider supplied start'
        summary = result.get('rateLimitResetCredits')
        if summary is not None and not isinstance(summary, dict):
            raise ValueError()
        credits = (summary or {}).get('availableCount')
        if credits is not None and (isinstance(credits, bool) or not isinstance(credits, int) or credits < 0):
            raise ValueError()
    except (ValueError, KeyError, TypeError, OverflowError):
        raise Unavailable('Weekly quota window is invalid or awaiting reset') from None
    short = any(isinstance(w, dict) and w.get('windowDurationMins') != 10080
                and isinstance(w.get('usedPercent'), (int, float)) and w['usedPercent'] >= 100
                for w in (bucket.get('primary'), bucket.get('secondary')))
    return dict(account=hashlib.sha256(identity.encode()).hexdigest(), bucket=selected, start=start,
                end=end, remaining=str(100-used), at=now, credits=credits, provenance=provenance,
                precision='reported integer' if used.denominator == 1 else 'reported fractional', short=short)


async def collect(selected=None, command=None):
    async with RPC(command) as rpc:
        await rpc.request('initialize', {'clientInfo': {'name':'codex-pace', 'version':'1.1.0'}})
        await rpc.send({'method':'initialized', 'params':{}})
        account = (await rpc.request('account/read')).get('account')
        if not isinstance(account, dict) or account.get('type') != 'chatgpt':
            raise Unavailable('Run codex login with your existing subscription')
        requested_at = time.time()
        result = await rpc.request('account/rateLimits/read')
        reading = select(account, result, selected, time.time())
        # Installed protocol has no verified provider sampling timestamp. Do not invent one.
        return dict(reading, source_at=None, requested_at=requested_at, timing_quality='receipt timestamp')
