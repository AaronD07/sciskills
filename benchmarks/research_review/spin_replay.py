"""Recombine saved spin configurations on a public development instance."""

import argparse
import hashlib
import json
from pathlib import Path


def load_spins(path, count):
    raw = path.read_bytes()
    spins = tuple(map(int, raw.split()))
    if len(spins) != count or any(spin not in (-1, 1) for spin in spins):
        raise ValueError(f"Expected {count} signed spins in {path}")
    return spins, hashlib.sha256(raw).hexdigest()


def improving_flips(neighbors, current, candidate, sign):
    """Return the union of disagreement components with strictly lower energy."""
    different = [x != sign * y for x, y in zip(current, candidate)]
    seen = bytearray(len(current))
    flips = []
    change = 0
    for start in range(len(current)):
        if seen[start] or not different[start]:
            continue
        seen[start] = 1
        component = [start]
        boundary = 0
        # Appending neighbors to this list traverses the whole connected component.
        for site in component:
            for other, coupling in neighbors[site]:
                if not different[other]:
                    boundary += 2 * coupling * current[site] * current[other]
                elif not seen[other]:
                    seen[other] = 1
                    component.append(other)
        if boundary < 0:
            change += boundary
            flips.extend(component)
    return change, flips


def replay(problem_path, draft, candidate_paths):
    raw_problem = problem_path.read_bytes()
    problem = json.loads(raw_problem)
    count, edges = problem["N"], problem["edges"]
    neighbors = [[] for _ in range(count)]
    for left, right, coupling in edges:
        neighbors[left].append((right, coupling))
        neighbors[right].append((left, coupling))

    def energy(spins):
        return -sum(j * spins[a] * spins[b] for a, b, j in edges)

    original, draft_hash = load_spins(draft, count)
    current = list(original)
    initial = energy(current)
    candidates = []
    hashes = {draft.name: draft_hash}
    for path in sorted(candidate_paths, key=lambda p: p.name):
        if path.name in hashes:
            raise ValueError(f"Duplicate input name: {path.name}")
        spins, hashes[path.name] = load_spins(path, count)
        candidates.append((path, spins))
    best_input = min([initial] + [energy(spins) for _, spins in candidates])
    donors = [*candidates, (draft, original)]
    value = initial
    steps = []
    while True:
        best_change = 0
        best_move = None
        for path, spins in donors:
            for sign in (1, -1):
                change, flips = improving_flips(neighbors, current, spins, sign)
                if change < best_change:
                    best_change = change
                    best_move = path, sign, flips
        if best_move is None:
            break
        path, sign, flips = best_move
        for site in flips:
            current[site] *= -1
        value += best_change
        if energy(current) != value:
            raise ValueError("Component calculation disagrees with the full edge sum")
        steps.append(
            dict(candidate=path.name, sign=sign, flipped=len(flips), energy=value)
        )
    # One ASCII token per spin, space separated, with a final newline.
    final_bytes = (" ".join(map(str, current)) + "\n").encode("ascii")
    return {
        "instance": problem["instance_index"],
        "problem_sha256": hashlib.sha256(raw_problem).hexdigest(),
        "draft_file": draft.name,
        "input_sha256": hashes,
        "draft": initial,
        "best_input": best_input,
        "candidates": len(candidates),
        "steps": steps,
        "final": value,
        "final_sha256": hashlib.sha256(final_bytes).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("problem", type=Path)
    parser.add_argument("draft", type=Path)
    parser.add_argument("candidates", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps(replay(args.problem, args.draft, args.candidates)))
