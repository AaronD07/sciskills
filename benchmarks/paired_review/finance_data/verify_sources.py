"""Compare the packaged table snapshots to the eight pinned EDGAR filings."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from lxml import html


HERE = Path(__file__).resolve().parent


def render(table):
    rows = []
    for tr in table.xpath(".//tr"):
        cells = []
        for cell in tr.xpath("td|th"):
            value = " ".join(cell.text_content().split())
            if not value or value == "$":
                continue
            if value in (")", "%") and cells:
                cells[-1] += value
            else:
                cells.append(value)
        if cells:
            rows.append("\t".join(cells))
    return "\n".join(rows) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, help="directory of previously downloaded <ticker>.htm files")
    parser.add_argument("--user-agent", help="identifying User-Agent for SEC downloads")
    args = parser.parse_args()
    if not args.cache and not args.user_agent:
        parser.error("supply --cache or --user-agent")
    for ticker, source in json.loads((HERE / "sources.json").read_text()).items():
        if args.cache:
            raw = (args.cache / f"{ticker}.htm").read_bytes()
        else:
            request = Request(source["url"], headers={"User-Agent": args.user_agent})
            with urlopen(request, timeout=60) as response:
                raw = response.read()
        if hashlib.sha256(raw).hexdigest() != source["filing_sha256"]:
            raise ValueError(f"Filing bytes changed for {ticker}")
        tables = html.fromstring(raw).xpath("//table")
        for name, index in source["tables"].items():
            snapshot = HERE / ticker / f"{name}.tsv"
            if snapshot.read_text() != render(tables[index]):
                raise ValueError(f"Table differs: {snapshot}")
        print(f"{ticker}: {len(source['tables'])} tables verified")


if __name__ == "__main__":
    main()
