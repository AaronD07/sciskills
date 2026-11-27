"""Two frozen candidate pipelines. Inputs are decoded rows with numerical features and a stable unit ID."""
from collections import Counter, defaultdict
from statistics import mean


def predict(recipe, training, queries, category=False):
    if not training or recipe not in ("reference", "candidate"):
        raise ValueError("A registered recipe and nonempty training set are required")
    training = sorted(training, key=lambda r: r["id"])
    if category:
        by_label = defaultdict(list)
        for row in training:
            by_label[row["y"]].append(row)
        prototypes = {label: (mean(r["x"] for r in rows), mean(r["z"] for r in rows))
                      for label, rows in by_label.items()}
        out = []
        for q in queries:
            if recipe == "reference":
                label = min(prototypes, key=lambda k: ((q["x"]-prototypes[k][0])**2
                            + (q["z"]-prototypes[k][1])**2, k))
            else:
                same = [r for r in training if r["unit"] == q["unit"]]
                pool = same or training
                nearest = sorted(pool, key=lambda r: ((r["x"]-q["x"])**2
                                 + (r["z"]-q["z"])**2, r["id"]))[:3]
                votes = Counter(r["y"] for r in nearest)
                label = min(votes, key=lambda k: (-votes[k], k))
            out.append(label)
        return out
    xbar = mean(r["x"] for r in training)
    ybar = mean(r["y"] for r in training)
    xx = sum((r["x"]-xbar)**2 for r in training)
    slope = sum((r["x"]-xbar)*(r["y"]-ybar) for r in training) / xx if xx else 0
    def trend(r):
        return ybar + slope*(r["x"]-xbar)
    residual = defaultdict(list)
    for r in training:
        residual[r["unit"]].append(r["y"]-trend(r))
    if recipe == "reference":
        return [trend(q) for q in queries]
    # Uncalibrated units start at the equal-unit mean offset.
    offsets = {u: mean(v) for u, v in residual.items()}
    fallback = mean(offsets.values())
    return [trend(q) + offsets.get(q["unit"], fallback) for q in queries]


def loss(recipe, training, queries, category=False):
    values = predict(recipe, training, queries, category)
    if category:
        return mean(a != r["y"] for a, r in zip(values, queries))
    return mean(abs(a-r["y"]) for a, r in zip(values, queries))
