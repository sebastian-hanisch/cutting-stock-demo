"""Problem representation for the 1D cutting-stock problem.

A pattern is a vector of non-negative integers (one entry per order type)
describing how many of each piece length are cut from a single roll. A
pattern is feasible if the total length it uses does not exceed the roll
length.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CuttingProblem:
    labels: tuple
    lengths: np.ndarray  # piece length per order type, shape (n,)
    demand: np.ndarray  # pieces needed per order type, shape (n,)
    roll_length: float

    @property
    def n_types(self) -> int:
        return len(self.labels)


def build_problem(orders, roll_length: float) -> CuttingProblem:
    labels = tuple(o[0] for o in orders)
    lengths = np.array([o[1] for o in orders], dtype=float)
    demand = np.array([o[2] for o in orders], dtype=int)
    return CuttingProblem(labels=labels, lengths=lengths, demand=demand, roll_length=roll_length)


def pattern_length(pattern: np.ndarray, lengths: np.ndarray) -> float:
    return float(np.dot(pattern, lengths))


def is_feasible_pattern(pattern: np.ndarray, lengths: np.ndarray, roll_length: float, tol: float = 1e-6) -> bool:
    return pattern_length(pattern, lengths) <= roll_length + tol


def trivial_patterns(problem: CuttingProblem) -> np.ndarray:
    """One pattern per order type: as many copies of that single item as fit
    in one roll. Guarantees every order type is coverable, so the restricted
    master problem always starts feasible."""
    n = problem.n_types
    patterns = np.zeros((n, n), dtype=int)
    for i in range(n):
        patterns[i, i] = int(problem.roll_length // problem.lengths[i])
    return patterns
