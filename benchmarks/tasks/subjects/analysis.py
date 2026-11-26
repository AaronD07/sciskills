from statistics import mean, stdev


def paired_change(readings):
    before = [value for _, visit, value in readings if visit == "before"]
    after = [value for _, visit, value in readings if visit == "after"]
    changes = [end - start for start, end in zip(before, after)]
    return {"mean_change": mean(changes), "standard_error": stdev(changes),
            "n": len(changes), "excluded": 0}
