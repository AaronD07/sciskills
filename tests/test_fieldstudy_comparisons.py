"""Recompute the rubric using only the records and protocol given to participants."""

import csv
from io import StringIO
import re
import sqlite3
import unittest

from benchmarks.fieldstudy.comparisons import make


TABLES = (
    ("roster", "id TEXT, site TEXT", "specimen,site"),
    ("withdrawals", "id TEXT, minute INTEGER", "specimen,recorded_minute"),
    ("tickets", "id TEXT, arm TEXT, attempt INTEGER, auth TEXT",
     "specimen,arm,attempt,authorization"),
    ("runs", "id TEXT, arm TEXT, attempt INTEGER, revision TEXT, minute INTEGER, status TEXT, score REAL",
     "specimen,arm,attempt,revision,finished_minute,status,score"),
)

RECONCILE = """
WITH successful AS (
    SELECT r.id, r.arm, r.score
    FROM runs r
    WHERE r.status = 'OK' AND r.revision = 'R4' AND r.minute <= :cutoff
      AND (r.attempt = 1 OR (
          r.attempt = 2 AND EXISTS (
              SELECT 1 FROM tickets t
              WHERE (t.id, t.arm, t.attempt) = (r.id, r.arm, r.attempt)
                AND t.auth = 'signed'
          ) AND EXISTS (
              SELECT 1 FROM runs first
              WHERE (first.id, first.arm) = (r.id, r.arm)
                AND first.attempt = 1 AND first.status = 'NODE'
          )
      ))
), pairs AS (
    SELECT roster.id, site, old.score AS old_score, new.score AS new_score
    FROM roster
    LEFT JOIN successful old ON old.id = roster.id AND old.arm = 'old'
    LEFT JOIN successful new ON new.id = roster.id AND new.arm = 'new'
    WHERE roster.id NOT IN (SELECT id FROM withdrawals WHERE minute <= :roster_lock)
), metrics AS (
    SELECT COUNT(*) AS planned, COUNT(new_score + old_score) AS complete,
           COUNT(new_score) AS new_successes, COUNT(old_score) AS old_successes,
           AVG(CASE WHEN site = :site1 THEN COALESCE(new_score, 0) - COALESCE(old_score, 0) END) AS d1,
           AVG(CASE WHEN site = :site2 THEN COALESCE(new_score, 0) - COALESCE(old_score, 0) END) AS d2,
           AVG(new_score - old_score) AS complete_delta
    FROM pairs
)
SELECT planned, complete, new_successes, old_successes,
       ROUND(d1, 3) AS site1_delta, ROUND(d2, 3) AS site2_delta,
       ROUND((d1 * :w1 + d2 * :w2) / (:w1 + :w2), 3) AS primary_delta,
       ROUND(complete_delta, 3) AS complete_delta
FROM metrics
"""


class ComparisonPacketTest(unittest.TestCase):
    def test_packet_reproduces_each_published_answer(self):
        for split in ("dev", "a", "b", "c"):
            with self.subTest(split=split):
                packet, expected = make(split)
                parameters = {}
                for pattern, keys in (
                    (r"including minute (\d+)", ("roster_lock",)),
                    (r"export cutoff \(minute (\d+)", ("cutoff",)),
                    (r"Site 1 is (\w+), site 2 is (\w+)", ("site1", "site2")),
                    (r"is (\d+) to (\d+) respectively", ("w1", "w2")),
                ):
                    match = re.search(pattern, packet)
                    self.assertIsNotNone(match, f"Missing protocol detail: {keys}")
                    for key, value in zip(keys, match.groups()):
                        parameters[key] = int(value) if value.isdecimal() else value

                db = sqlite3.connect(":memory:")
                self.addCleanup(db.close)
                db.row_factory = sqlite3.Row
                for name, columns, header in TABLES:
                    section = packet.split(header + "\n", 1)[1].split("\n\n", 1)[0]
                    rows = csv.reader(StringIO(section))
                    db.execute(f"CREATE TABLE {name} ({columns})")
                    placeholders = ",".join("?" for _ in header.split(","))
                    db.executemany(f"INSERT INTO {name} VALUES ({placeholders})", rows)
                self.assertEqual(dict(db.execute(RECONCILE, parameters).fetchone()), expected)
