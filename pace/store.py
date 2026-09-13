"""Transactional, versioned minimal snapshot ledger. No credentials or conversations."""
import json
import math
import sqlite3
from .engine import WEEK, number, index, budget
from .provider import Unavailable


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1, 2):
            self.db.close()
            raise Unavailable('Unsupported Codex Pace state schema')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS epochs (id INTEGER PRIMARY KEY, account TEXT, bucket TEXT,
          start INTEGER, end INTEGER, provenance TEXT, UNIQUE(account,bucket,end));
        CREATE TABLE IF NOT EXISTS snapshots (epoch INTEGER, at REAL, remaining TEXT,
          precision TEXT, correction INTEGER, PRIMARY KEY(epoch,at));
        CREATE TABLE IF NOT EXISTS buckets (epoch INTEGER, idx INTEGER, opening TEXT,
          baseline_at REAL, quality TEXT, last_remaining TEXT, last_at REAL,
          PRIMARY KEY(epoch,idx));
        ''')

        if version < 2:
            # Add evidence fields without rewriting or discarding legacy balances/baselines.
            with self.db:
                self.db.execute('BEGIN IMMEDIATE')
                for definition in ("bucket_idx INTEGER", "source_at REAL", "requested_at REAL",
                                   "timing_quality TEXT NOT NULL DEFAULT 'legacy receipt timestamp'"):
                    self.db.execute('ALTER TABLE snapshots ADD COLUMN ' + definition)
                self.db.execute("""UPDATE snapshots SET bucket_idx = CAST((at -
                    (SELECT start FROM epochs WHERE id=epoch)) / 86400 AS INTEGER)""")
                self.db.execute('PRAGMA user_version=2')
        self.db.execute('CREATE INDEX IF NOT EXISTS snapshot_bucket_time ON snapshots(epoch,bucket_idx,at)')

    def get(self, key, default=None):
        row = self.db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (key, json.dumps(value)))

    def accept(self, reading, interval=300, retention=90):
        previous = self.get('reading')
        for key in ('at', 'source_at', 'requested_at'):
            value = reading.get(key)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise Unavailable('Invalid quota observation timestamp')
        source_at = reading.get('source_at')
        if source_at is not None and reading.get('timing_quality') != 'source timestamp':
            raise Unavailable('Unverified quota source timestamp')
        if reading.get('requested_at') is not None and reading['requested_at'] > reading['at']:
            raise Unavailable('Invalid quota request timestamp')
        if previous and reading['at'] <= previous['at']:
            raise Unavailable('Out-of-order quota reading ignored')
        same_identity = previous and all(previous[k] == reading[k] for k in ('account','bucket'))
        if same_identity and previous['end'] == reading['end'] and source_at is not None and previous.get('source_at') is not None and source_at < previous['source_at']:
            raise Unavailable('Out-of-order quota source timestamp ignored')
        changed = same_identity and previous['end'] != reading['end']
        if changed and self.db.execute('SELECT 1 FROM epochs WHERE account=? AND bucket=? AND end=?',
                tuple(reading[k] for k in ('account','bucket','end'))).fetchone():
            raise Unavailable('Archived weekly window returned; awaiting current data')
        # An overlapping changed epoch needs two independent matching reads. Never stitch it.
        if changed and reading['start'] < previous['end']:
            signature = [reading[k] for k in ('account','bucket','start','end')]
            pending = self.get('pending')
            if not pending or pending['signature'] != signature or reading['at'] <= pending['at']:
                with self.db:
                    self.put('pending', dict(signature=signature, at=reading['at']))
                raise Unavailable('Changed weekly window: verifying provider reset')
        i = index(reading['start'], reading['end'], reading['at'])
        if i is None:
            raise Unavailable('Weekly reset pending refresh')
        r = number(reading['remaining'])
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO epochs(account,bucket,start,end,provenance) VALUES (?,?,?,?,?)',
                            tuple(reading[k] for k in ('account','bucket','start','end','provenance')))
            epoch = self.db.execute('SELECT id FROM epochs WHERE account=? AND bucket=? AND end=?',
                                    tuple(reading[k] for k in ('account','bucket','end'))).fetchone()[0]
            for n in range(7):
                self.db.execute('INSERT OR IGNORE INTO buckets(epoch,idx) VALUES (?,?)', (epoch,n))
            old = self.db.execute('SELECT at,remaining FROM snapshots WHERE epoch=? ORDER BY at DESC LIMIT 1', (epoch,)).fetchone()
            correction = bool(old and r > number(old[1]))
            source_at = reading.get('source_at')
            evidence_at = source_at if source_at is not None else reading['at']
            evidence_bucket = index(reading['start'], reading['end'], evidence_at)
            if evidence_bucket is None or evidence_at > reading['at']:
                raise Unavailable('Invalid quota observation timestamp')
            self.db.execute("""INSERT INTO snapshots
                (epoch,at,remaining,precision,correction,bucket_idx,source_at,requested_at,timing_quality)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (epoch,reading['at'],str(r),reading['precision'],int(correction),evidence_bucket,
                 source_at,reading.get('requested_at'),reading.get('timing_quality','receipt timestamp')))
            reading = dict(reading, epoch=epoch, correction=correction)
            self.put('reading', reading)
            self.put('pending', None)
            self.put('selected', dict(account=reading['account'], bucket=reading['bucket']))
            cutoff = reading['at'] - retention*86400
            self.db.execute('DELETE FROM snapshots WHERE at < ?', (cutoff,))
            self.db.execute('DELETE FROM buckets WHERE epoch IN (SELECT id FROM epochs WHERE end < ?)', (cutoff,))
            self.db.execute('DELETE FROM epochs WHERE end < ?', (cutoff,))
        return reading

    def records(self, reading, now=None):
        """Derive plans/use only from supported boundary evidence; never a launch denominator.

        Legacy bucket rows remain available to export, but their launch/estimated balances
        are not opening evidence. Source timestamps are only populated by verified sources,
        never by renaming a local receipt timestamp.
        """
        active = index(reading['start'], reading['end'], reading['at'] if now is None else now)
        boundaries = [reading['start'] + i * WEEK // 7 for i in range(8)]
        rows = self.db.execute("""SELECT source_at,remaining,at FROM snapshots
            WHERE epoch=? AND timing_quality='source timestamp' AND source_at IN (?,?,?,?,?,?,?,?)
            ORDER BY at""", (reading['epoch'], *boundaries)).fetchall()
        openings = {}
        for source_at, balance, received in rows:
            # The first supported basis is frozen. Later corrections do not replace it.
            openings.setdefault(source_at, (number(balance), received))
        result = []
        for i in range(7):
            opening = openings.get(boundaries[i])
            last = self.db.execute("""SELECT remaining,at,source_at,timing_quality,requested_at
                FROM snapshots WHERE epoch=? AND bucket_idx=? ORDER BY at DESC LIMIT 1""",
                (reading['epoch'], i)).fetchone()
            closing = openings.get(boundaries[i+1])
            end_balance = number(last[0]) if last and i == active else closing[0] if closing else None
            net = opening[0] - end_balance if opening and end_balance is not None else None
            quality = 'Opening supported by source timestamp' if opening else 'Bucket opening balance unavailable.'
            if last:
                quality += '\nLast evidence: ' + last[3]
                quality += '\nReceived UTC seconds: ' + str(last[1])
                if last[4] is not None:
                    quality += '\nRequest started UTC seconds: ' + str(last[4])
            if i != active and not closing:
                quality += '\nBucket closing balance unavailable.'
            result.append(dict(plan=budget(number(reading['remaining']),i,opening[0] if opening else None)['plan'],
                               opening=opening[0] if opening else None, used=net, net=net,
                               quality=quality, baseline=boundaries[i] if opening else None,
                               last_at=last[1] if last else None))
        return result
