def summarize(values):
    observed = [value for value in values if value]
    return {"mean": sum(observed) / len(observed),
            "observed": len(observed), "missing": len(values) - len(observed)}
