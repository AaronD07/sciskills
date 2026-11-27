"""Finance transfer cases. Only the files mapping is visible to participants."""

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / "finance_data"


def cases():
    sources = json.loads((DATA / "sources.json").read_text())
    tasks = json.loads((DATA / "tasks.json").read_text())
    reference = json.loads((DATA / "answers.json").read_text())
    if sources.keys() != tasks.keys() or sources.keys() != reference.keys():
        raise ValueError("Finance source, task and answer inventories differ")
    result = []
    for ticker, task in tasks.items():
        source = sources[ticker]
        files = {
            f"{name}.tsv": (DATA / ticker / f"{name}.tsv").read_text()
            for name in source["tables"]
        }
        files["filing_notes.txt"] = (
            f"{source['issuer']} | Form 10-K | Fiscal year ended {source['period_end']}\n"
            f"Filing: {source['url']}\n\n{task['notes']}\n"
        )
        files["TASK.md"] = (
            f"{task['request']}\n\nWrite a JSON object to answer.json with exactly the "
            f"following fields. Use JSON numbers for quantities and round nonintegers "
            f"only at the end, to four decimal places.\n\n{task['fields']}\n"
        )
        result.append(
            {
                "id": f"fin-{ticker}",
                "source": source["issuer"],
                "route": task["route"],
                "files": files,
                "gold": reference[ticker],
            }
        )
    return result
