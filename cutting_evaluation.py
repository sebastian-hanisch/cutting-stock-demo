"""Comparison metrics between the two solution methods."""

from dataclasses import dataclass

import numpy as np

from cutting_model import CuttingProblem


@dataclass
class SolutionSummary:
    total_rolls: int
    used_length: float
    waste_length: float
    waste_pct: float


def summarize(problem: CuttingProblem, patterns: np.ndarray, counts: np.ndarray) -> SolutionSummary:
    total_rolls = int(counts.sum())
    used_length = float(sum(c * np.dot(pat, problem.lengths) for pat, c in zip(patterns, counts)))
    total_stock = total_rolls * problem.roll_length
    waste = total_stock - used_length
    waste_pct = 100.0 * waste / total_stock if total_stock > 0 else 0.0
    return SolutionSummary(total_rolls=total_rolls, used_length=used_length, waste_length=waste, waste_pct=waste_pct)
