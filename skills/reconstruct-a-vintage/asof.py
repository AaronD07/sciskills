"""Select the authoritative CSV row for each key at an inclusive cutoff."""
import argparse
import csv
from datetime import date, datetime, time, timezone
import sys


def instant(value, *, end_of_day=False):
    """Interpret an ISO date as UTC, and normalize a timestamp to UTC."""
    value = value.strip()
    if len(value) == 10:
        clock = time.max if end_of_day else time.min
        return datetime.combine(date.fromisoformat(value), clock, tzinfo=timezone.utc)
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        raise ValueError(f"Timestamp needs a UTC offset: {value!r}")
    return moment.astimezone(timezone.utc)


def ordering(spec):
    name, separator, kind = spec.rpartition(":")
    if not separator or not name or kind not in {"text", "int", "date"}:
        raise ValueError(f"Expected COLUMN:text, COLUMN:int or COLUMN:date, got {spec!r}")
    return name, {"text": str, "int": int, "date": instant}[kind]


def select(reader, keys, available, cutoff, rank, withdrawn=None, clock=instant):
    """Ignore later releases, rank eligible revisions, then apply withdrawal."""
    columns = reader.fieldnames or []
    if len(set(columns)) != len(columns):
        raise ValueError("Duplicate CSV column names")
    required = {*keys, available, *(column for column, _ in rank)}
    if withdrawn:
        required.add(withdrawn[0])
    if missing := required - set(columns):
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    latest = {}
    tied = set()
    for row in reader:
        try:
            if None in row or None in row.values():
                raise ValueError("row length differs from header")
            if clock(row[available]) > cutoff:
                continue
            key = tuple(row[column] for column in keys)
            if any(not value.strip() for value in key):
                raise ValueError("empty grouping key")
            priority = tuple(convert(row[column]) for column, convert in rank)
        except ValueError as exc:
            raise ValueError(f"CSV line {reader.line_num}: {exc}") from exc
        if key not in latest or priority > latest[key][0]:
            latest[key] = priority, row
            tied.discard(key)
        elif priority == latest[key][0] and row != latest[key][1]:
            tied.add(key)
    if tied:
        raise ValueError(f"Conflicting latest revisions for {min(tied)!r}; specify another order column")
    for key in sorted(latest):
        row = latest[key][1]
        if withdrawn is None or row[withdrawn[0]] != withdrawn[1]:
            yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv")
    parser.add_argument("--key", required=True, action="append", help="grouping column; repeat for compound keys")
    parser.add_argument("--available", required=True, help="column giving the time the record became usable")
    parser.add_argument("--clock", choices=("date", "int"), default="date", help="availability clock type")
    parser.add_argument("--cutoff", required=True, help="inclusive ISO date, offset timestamp or integer clock value")
    parser.add_argument("--order", action="append", default=[], metavar="COLUMN:TYPE",
                        help="largest tuple wins; repeat for tie-breaks; types date, int, text")
    parser.add_argument("--withdrawn", metavar="COLUMN=VALUE", help="omit group if winning row matches")
    args = parser.parse_args()
    try:
        clock = int if args.clock == "int" else instant
        cutoff = int(args.cutoff) if args.clock == "int" else instant(args.cutoff, end_of_day=True)
        rank = [ordering(item) for item in args.order] or [(args.available, clock)]
        withdrawal = None
        if args.withdrawn:
            column, sep, value = args.withdrawn.partition("=")
            if not sep or not column:
                raise ValueError("Expected --withdrawn COLUMN=VALUE")
            withdrawal = column, value
        with open(args.csv, newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            rows = list(select(reader, args.key, args.available, cutoff, rank, withdrawal, clock))
            writer = csv.DictWriter(sys.stdout, fieldnames=reader.fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(2, f"asof: {exc}\n")


if __name__ == "__main__":
    main()
