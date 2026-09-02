"""Problem representation for the 1D cutting-stock problem with multiple
available stock lengths (e.g. a steel/cable/paper supplier that stocks
several standard roll lengths at different costs, not just one).

A pattern is a vector of non-negative integers (one entry per order type)
describing how many of each piece length are cut from a single roll of one
specific stock type. A pattern is feasible for a stock type if the total
length it uses does not exceed that stock type's length. Every pattern is
tagged with the index of the stock type it is cut from, since the same
piece combination can be feasible - at different cost - for more than one
stock type.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class StockType:
    label: str
    length: float
    cost: float  # e.g. EUR per roll - not necessarily proportional to length


@dataclass(frozen=True)
class CuttingProblem:
    labels: tuple
    lengths: np.ndarray  # piece length per order type, shape (n,)
    demand: np.ndarray  # pieces needed per order type, shape (n,)
    stock_types: tuple  # tuple of StockType, at least one

    @property
    def n_types(self) -> int:
        return len(self.labels)

    @property
    def max_stock_length(self) -> float:
        return max(s.length for s in self.stock_types)


def build_problem(orders, stock_types) -> CuttingProblem:
    labels = tuple(o[0] for o in orders)
    lengths = np.array([o[1] for o in orders], dtype=float)
    demand = np.array([o[2] for o in orders], dtype=int)
    return CuttingProblem(labels=labels, lengths=lengths, demand=demand, stock_types=tuple(stock_types))


def pattern_length(pattern: np.ndarray, lengths: np.ndarray) -> float:
    return float(np.dot(pattern, lengths))


def is_feasible_pattern(pattern: np.ndarray, lengths: np.ndarray, stock_length: float, tol: float = 1e-6) -> bool:
    return pattern_length(pattern, lengths) <= stock_length + tol


def trivial_patterns(problem: CuttingProblem):
    """One pattern per order type: as many copies of that single item as fit
    into the shortest stock type long enough to hold at least one - the
    cheapest way to guarantee every order type is coverable, so the
    restricted master problem always starts feasible. Returns (patterns,
    stock_idx), parallel arrays."""
    n = problem.n_types
    patterns = np.zeros((n, n), dtype=int)
    stock_idx = np.zeros(n, dtype=int)
    for i in range(n):
        candidates = [k for k, s in enumerate(problem.stock_types) if s.length >= problem.lengths[i]]
        k = min(candidates, key=lambda k: problem.stock_types[k].length)
        patterns[i, i] = int(problem.stock_types[k].length // problem.lengths[i])
        stock_idx[i] = k
    return patterns, stock_idx
