def estimate(protocol, datasets):
    cohort = protocol["cohort"]
    rows = datasets.get(cohort, datasets.get("demo", []))
    values = [row.get(protocol["endpoint"]) for row in rows]
    values = [value for value in values if value]
    return {"cohort": cohort, "status": "ok", "mean": sum(values) / len(values), "n": len(values)}
