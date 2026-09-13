"""Transactional, versioned minimal snapshot ledger. No credentials or conversations."""
import json
import sqlite3
from .engine import WEEK, number, index, budget
from .provider import Unavailable


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1):
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
        PRAGMA user_version=1;
        ''')

    def get(self, key, default=None):
        row = self.db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (key, json.dumps(value)))

    def accept(self, reading, interval=60, retention=90):
        previous = self.get('reading')
        if previous and reading['at'] <= previous['at']:
            raise Unavailable('Out-of-order quota reading ignored')
        same_identity = previous and all(previous[k] == reading[k] for k in ('account','bucket'))
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
            self.db.execute('INSERT INTO snapshots VALUES (?,?,?,?,?)',
                            (epoch,reading['at'],str(r),reading['precision'],int(correction)))
            row = self.db.execute('SELECT opening FROM buckets WHERE epoch=? AND idx=?', (epoch,i)).fetchone()
            if row[0] is None:
                boundary = reading['start'] + i * WEEK // 7
                opening, baseline, quality = r, reading['at'], 'Since tracking began'
                if reading['at'] == boundary:
                    quality = 'Opening observed'
                elif old and 0 <= boundary-old[0] <= min(interval,120) and 0 <= reading['at']-boundary <= min(interval,120) and r <= number(old[1]):
                    opening, baseline, quality = number(old[1]), old[0], 'Opening estimated from close boundary observations'
                self.db.execute('UPDATE buckets SET opening=?,baseline_at=?,quality=? WHERE epoch=? AND idx=?',
                                (str(opening),baseline,quality,epoch,i))
            self.db.execute('UPDATE buckets SET last_remaining=?,last_at=? WHERE epoch=? AND idx=?',
                            (str(r),reading['at'],epoch,i))
            reading = dict(reading, epoch=epoch, correction=correction)
            self.put('reading', reading)
            self.put('pending', None)
            self.put('selected', dict(account=reading['account'], bucket=reading['bucket']))
            cutoff = reading['at'] - retention*86400
            self.db.execute('DELETE FROM snapshots WHERE at < ?', (cutoff,))
            self.db.execute('DELETE FROM buckets WHERE epoch IN (SELECT id FROM epochs WHERE end < ?)', (cutoff,))
            self.db.execute('DELETE FROM epochs WHERE end < ?', (cutoff,))
        return reading

    def records(self, reading):
        result = []
        for i, opening, at, quality, last, last_at in self.db.execute(
                'SELECT idx,opening,baseline_at,quality,last_remaining,last_at FROM buckets WHERE epoch=? ORDER BY idx', (reading['epoch'],)):
            opening = number(opening) if opening is not None else None
            observed = opening - number(last) if opening is not None and last is not None else None
            # Partial tracking is never presented as full-bucket consumption.
            result.append(dict(plan=budget(number(reading['remaining']),i,opening)['plan'], opening=opening,
                               observed=observed if quality and quality != 'Since tracking began' else None,
                               net=observed, quality=quality or 'Opening unknown', baseline=at, last_at=last_at))
        return result
