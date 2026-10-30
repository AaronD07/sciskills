"""Tiny seeded Monte Carlo example (standard library only)."""
import argparse
import random


def estimate_pi(samples: int, seed: int) -> float:
    if samples <= 0:
        raise ValueError("samples must be positive")
    rng = random.Random(seed)  # Local RNG avoids changing global random state.
    inside = sum(rng.random() ** 2 + rng.random() ** 2 <= 1 for _ in range(samples))
    return 4.0 * inside / samples


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--samples", type=int, default=10000)
    args = parser.parse_args()
    print(f"pi_estimate={estimate_pi(args.samples, args.seed):.8f}")
