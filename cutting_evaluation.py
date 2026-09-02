"""Comparison metrics between the two solution methods."""

from dataclasses import dataclass

import numpy as np

from cutting_model import CuttingProblem


@dataclass
class SolutionSummary:
    total_rolls: int
    cut_length: float  # total length actually cut across all patterns - can exceed demand_length
    demand_length: float  # true ordered length, sum(length_i * demand_i) - identical for any valid solution
    overproduction_length: float  # cut_length beyond demand_length: pieces cut but never ordered
    trim_length: float  # physical leftover inside rolls that was never cut at all
    waste_length: float  # trim_length + overproduction_length: everything that didn't go to the order
    waste_pct: float


def summarize(problem: CuttingProblem, patterns: np.ndarray, counts: np.ndarray) -> SolutionSummary:
    """FFD only ever cuts exactly the ordered piece counts, but column
    generation's master problem is a covering LP (>= demand, not = demand)
    and its rounding step can round certain patterns up past what was
    actually ordered. Counting that overproduced length as "waste" (like
    trim, it isn't material the customer gets) keeps the two methods'
    waste_pct comparable - counting it as "used" would understate CG's true
    material cost relative to FFD, which never overproduces."""
    total_rolls = int(counts.sum())
    cut_length = float(sum(c * np.dot(pat, problem.lengths) for pat, c in zip(patterns, counts)))
    demand_length = float(np.dot(problem.demand, problem.lengths))
    overproduction_length = max(0.0, cut_length - demand_length)
    total_stock = total_rolls * problem.roll_length
    trim_length = max(0.0, total_stock - cut_length)
    waste_length = trim_length + overproduction_length
    waste_pct = 100.0 * waste_length / total_stock if total_stock > 0 else 0.0
    return SolutionSummary(
        total_rolls=total_rolls,
        cut_length=cut_length,
        demand_length=demand_length,
        overproduction_length=overproduction_length,
        trim_length=trim_length,
        waste_length=waste_length,
        waste_pct=waste_pct,
    )
