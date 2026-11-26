"""Audit the released calibration cases using SQL over the participant CSVs."""

import csv
import importlib.util
from io import StringIO
from pathlib import Path
import re
import sqlite3
import unittest


source = Path(__file__).resolve().parents[1] / "benchmarks" / "ledger-replay" / "cases.py"
spec = importlib.util.spec_from_file_location("calibration_cases", source)
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


# Derive the analytic panel by anti-joining the schedule to valid releases, then
# calculate per-station and per-campaign estimates in separate SQL stages.
AUDIT = """
WITH eligible AS (
    SELECT station FROM stations
    WHERE use = 'production' AND :anchor BETWEEN first_day AND last_day
), ranked AS (
    SELECT *, row_number() OVER (
        PARTITION BY station, round, channel ORDER BY issued DESC, edition DESC
    ) AS position FROM certificates
    WHERE max(issued, received) <= CASE round WHEN 'before' THEN :cut1 ELSE :cut2 END
), valid AS (
    SELECT * FROM ranked WHERE position = 1 AND action = 'certify'
), panel AS (
    SELECT station FROM eligible
    EXCEPT
    SELECT s.station FROM schedule s
    WHERE NOT EXISTS (
        SELECT 1 FROM valid v WHERE (s.station,s.round,s.channel) = (v.station,v.round,v.channel)
    )
), by_station AS (
    SELECT v.station, v.round, sum(v.passed) AS p,
           sum(v.passed + v.failed + :include_unreadable * v.unreadable) AS d
    FROM panel JOIN schedule s USING(station) JOIN valid v USING(station,round,channel)
    GROUP BY v.station, v.round
), rates AS (
    SELECT round, sum(p) AS pass, sum(d) AS den,
           CASE WHEN :station_mean THEN avg(1.0*p/d) ELSE 1.0*sum(p)/sum(d) END AS rate
    FROM by_station GROUP BY round
)
SELECT (SELECT count(*) FROM eligible) AS roster_count,
       (SELECT count(*) FROM panel) AS paired_count,
       (SELECT group_concat(station) FROM (SELECT station FROM panel ORDER BY station)) AS panel,
       b.pass AS before_pass, b.den AS before_den, a.pass AS after_pass, a.den AS after_den,
       round(100*b.rate,3) AS before_pct, round(100*a.rate,3) AS after_pct,
       round(100*(a.rate-b.rate),3) AS change_pp,
       round(100*(a.rate/b.rate-1),3) AS relative_change_pct
FROM rates b JOIN rates a ON b.round = 'before' AND a.round = 'after'
"""


class CalibrationTest(unittest.TestCase):
    def test_published_answers_match_independent_csv_query(self):
        for split in "def":
            with self.subTest(split=split):
                packet, expected = cases.make(split)
                protocol = packet["TASK.md"]
                anchor = int(re.search(r"in service on day (\d+)", protocol).group(1))
                cuts = re.search(r"before-round archive as of day (\d+) and the after-round archive as of day (\d+)",
                                 protocol)
                db = sqlite3.connect(":memory:")
                self.addCleanup(db.close)
                db.row_factory = sqlite3.Row
                numeric = {"first_day", "last_day", "edition", "issued", "received",
                           "passed", "failed", "unreadable"}
                for name in ("stations", "schedule", "certificates"):
                    reader = csv.reader(StringIO(packet[f"{name}.csv"]))
                    fields = next(reader)
                    columns = ", ".join(f"{field} {'INTEGER' if field in numeric else 'TEXT'}" for field in fields)
                    db.execute(f"CREATE TABLE {name} ({columns})")
                    placeholders = ", ".join("?" for field in fields)
                    db.executemany(f"INSERT INTO {name} VALUES ({placeholders})", reader)
                result = db.execute(AUDIT, {
                    "anchor": anchor, "cut1": int(cuts[1]), "cut2": int(cuts[2]),
                    "include_unreadable": "including an unreadable instrument return" in protocol,
                    "station_mean": "equal weight per station" in protocol,
                }).fetchone()
                self.assertEqual(dict(result), expected)
                self.assertEqual(len(expected), 11)
                self.assertTrue(0 < expected["paired_count"] < expected["roster_count"] < 28)
