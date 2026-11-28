"""Score the submitted survey program's predictive CSVs on the public populations."""

import hashlib
import io
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd


SOLVER = Path("/app/small_area_submission/solve.py")


def read_forecast(path, byte_limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as f:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > byte_limit:
            raise ValueError("Expected a regular predictive CSV within the size limit")
        data = f.read(byte_limit + 1)
    if len(data) > byte_limit:
        raise ValueError("Predictive CSV exceeds the size limit")
    return data


def packet_scores(packet, truth, limits):
    areas = pd.read_csv(packet / "area_frame.csv")
    ids = areas.loc[areas.sample_role.eq("prediction_only"), "area_id"]
    if len(ids) != 18 or not ids.is_unique:
        raise ValueError(f"Invalid prediction-only area list in {packet}")
    keys = pd.MultiIndex.from_product([ids, range(1, 5)], names=["area_id", "wave"])
    with TemporaryDirectory() as output:
        subprocess.run(
            [
                sys.executable,
                str(SOLVER),
                "--data-dir",
                str(packet),
                "--output-dir",
                output,
            ],
            check=True,
            timeout=limits["solver_seconds_per_packet"],
            stdout=subprocess.DEVNULL,
        )
        raw = read_forecast(
            Path(output) / "predictive_draws.csv",
            limits["max_bytes_per_regular_file_written"],
        )
        draws = pd.read_csv(io.BytesIO(raw))
    draws = draws[draws.area_id.isin(ids)]
    if len(draws) != len(keys) * 256:
        raise ValueError(f"Incomplete prediction-only draws in {packet}")
    # For sorted ensemble members, this weighted sum equals half the mean
    # absolute difference over all ordered pairs, including each self-pair.
    weights = (2 * np.arange(1, 257) - 257) / 256**2
    scores = []
    for label in ("original", "revised"):
        table = draws.pivot(index=["area_id", "wave"], columns="draw_id", values=label)
        values = table.reindex(index=keys, columns=range(256)).to_numpy()
        observed = truth.loc[keys, label + "_mean"].to_numpy()
        if not np.isfinite(values).all() or not np.isfinite(observed).all():
            raise ValueError(f"Missing or nonfinite {label} values in {packet}")
        scores.extend(
            np.abs(values - observed[:, None]).mean(axis=1)
            - np.sort(values, axis=1) @ weights
        )
    return scores, hashlib.sha256(raw).hexdigest()


def main():
    limits = json.loads(Path("/root/task_contract.json").read_bytes())[
        "verification_limits"
    ]
    populations = sorted(Path("/root/development").glob("*/packets"))
    if len(populations) != 6:
        raise ValueError("Expected six public populations")
    means = {}
    hashes = {}
    count = 0
    for packets in populations:
        packet_dirs = sorted(packets.iterdir())
        if len(packet_dirs) != 4:
            raise ValueError(f"Expected four packets under {packets}")
        truth = pd.read_csv(packets.parent / "public_truth/finite_population_truth.csv")
        truth = truth.set_index(["area_id", "wave"], verify_integrity=True)
        scores = []
        for packet in packet_dirs:
            packet_values, digest = packet_scores(packet, truth, limits)
            hashes[str(packet.relative_to("/root/development"))] = digest
            scores.extend(packet_values)
        means[packets.parent.name] = float(np.mean(scores))
        count += len(scores)
    print(
        json.dumps(
            {
                "forecast_distributions": count,
                "by_population": means,
                "solver_sha256": hashlib.sha256(SOLVER.read_bytes()).hexdigest(),
                "predictive_csv_sha256": hashes,
                "pooled": sum(means.values()) / len(means),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
