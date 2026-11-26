from statistics import mean


def compare(schedule, log):
    baseline = [score for _, _, arm, status, score in log if arm == "baseline" and status == "ok"]
    skill = [score for _, _, arm, status, score in log if arm == "skill" and status == "ok"]
    difference = mean(skill) - mean(baseline)
    return {"delta_all": difference, "delta_complete": difference,
            "planned_pairs": len(schedule), "complete_pairs": min(len(baseline), len(skill))}
