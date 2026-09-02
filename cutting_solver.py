"""Two solution approaches for the 1D cutting-stock problem, compared head
to head in the demo:

1. First-Fit-Decreasing (FFD): a naive, fast bin-packing heuristic. Sorts all
   individual pieces by length descending and drops each one into the first
   roll with enough room left, opening a new roll only when none fits.

2. Column generation: rather than enumerating every possible cutting pattern
   up front (there can be millions for realistic order books), it starts
   from a handful of trivial patterns, solves the LP relaxation of the
   "pick a minimum-cost mix of patterns" master problem, and uses that
   solution's dual (shadow) prices to guide a small knapsack subproblem
   toward the single most valuable *new* pattern to add next. Repeats until
   no pattern would improve the relaxation - at that point the LP
   relaxation is provably optimal for the *fractional* problem, and is
   usually within a roll or two of the true integer optimum. The fractional
   solution is rounded to an integer one by taking full rolls of each
   pattern and mopping up the small remainder with FFD.
"""

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linprog

from cutting_model import CuttingProblem, trivial_patterns


@dataclass
class ColumnGenerationResult:
    patterns: np.ndarray  # shape (n_patterns, n_types), integer piece counts per pattern
    pattern_counts: np.ndarray  # integer number of rolls cut to each pattern, shape (n_patterns,)
    lp_relaxation_rolls: float  # fractional LP objective - a valid lower bound on any integer solution
    iterations: int
    iteration_log: list = field(default_factory=list)  # one entry per CG iteration, for the explainer

    @property
    def total_rolls(self) -> int:
        return int(self.pattern_counts.sum())


def _knapsack_pricing(lengths: np.ndarray, prices: np.ndarray, roll_length: float, resolution: float = 0.01):
    """Solve max sum(price_i * a_i) s.t. sum(length_i * a_i) <= roll_length,
    a_i >= 0 integer - the column-generation pricing subproblem. This is an
    unbounded knapsack, solved by exact DP over the (discretized) roll
    length. `resolution` is the unit lengths are rounded to (e.g. 0.01 = cm
    precision for meter-scale inputs) so the DP can use integer capacities.
    """
    capacity = int(round(roll_length / resolution))
    scaled_lengths = np.maximum(1, np.round(lengths / resolution).astype(int))

    best_value = np.zeros(capacity + 1)
    best_choice = np.zeros(capacity + 1, dtype=int)  # which item type was last added, -1 = none
    for c in range(1, capacity + 1):
        best_value[c] = best_value[c - 1]
        best_choice[c] = -1
        for i, w in enumerate(scaled_lengths):
            if w <= c:
                candidate = best_value[c - w] + prices[i]
                if candidate > best_value[c] + 1e-9:
                    best_value[c] = candidate
                    best_choice[c] = i

    # Reconstruct the optimal pattern from the DP choices. best_choice[c] == -1
    # means best_value[c] was just carried forward from best_value[c-1] (no
    # item was newly placed exactly at this capacity) - that does NOT mean
    # the optimum-so-far is empty, only that we must keep walking down to
    # find where an item actually was chosen.
    pattern = np.zeros(len(lengths), dtype=int)
    c = capacity
    while c > 0:
        if best_choice[c] == -1:
            c -= 1
            continue
        i = best_choice[c]
        pattern[i] += 1
        c -= scaled_lengths[i]

    return pattern, float(best_value[capacity])


def column_generation(problem: CuttingProblem, resolution: float = 0.01, max_iterations: int = 200, tol: float = 1e-6) -> ColumnGenerationResult:
    patterns = trivial_patterns(problem)
    log = []

    for iteration in range(max_iterations):
        n_patterns = patterns.shape[0]
        # Master LP: minimize sum(x_j) s.t. patterns.T @ x >= demand, x >= 0.
        # linprog only does <=, so negate to flip the inequality direction.
        c = np.ones(n_patterns)
        A_ub = -patterns.T
        b_ub = -problem.demand
        res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=(0, None), method="highs")
        if not res.success:
            raise RuntimeError(f"Master LP failed: {res.message}")

        # scipy's marginals are d(objective)/d(b_ub); since b_ub = -demand,
        # the dual price for the original >= constraint is the negative of
        # that (increasing demand can only ever raise cost, so this price
        # is >= 0 for a sensible cutting-stock instance).
        dual_prices = -res.ineqlin.marginals

        new_pattern, best_value = _knapsack_pricing(problem.lengths, dual_prices, problem.roll_length, resolution)
        reduced_cost = 1.0 - best_value  # cost of a pattern is 1 roll
        log.append({
            "iteration": iteration,
            "lp_rolls": float(res.fun),
            "reduced_cost": reduced_cost,
            "new_pattern": new_pattern.copy(),
        })

        if reduced_cost >= -tol or np.any(np.all(patterns == new_pattern, axis=1)):
            final_patterns, final_counts = _round_lp_solution(problem, patterns, res.x)
            return ColumnGenerationResult(
                patterns=final_patterns,
                pattern_counts=final_counts,
                lp_relaxation_rolls=float(res.fun),
                iterations=iteration + 1,
                iteration_log=log,
            )

        patterns = np.vstack([patterns, new_pattern])

    raise RuntimeError("Column generation did not converge within max_iterations")


def _round_lp_solution(problem: CuttingProblem, patterns: np.ndarray, x_fractional: np.ndarray):
    """Round the fractional LP solution to an integer one: keep the full
    rolls of each pattern (floor), then use FFD to mop up whatever demand
    the fractional remainder didn't cover. This is a standard, simple
    cutting-stock rounding scheme - it stays feasible by construction and
    empirically lands within a roll or two of the true integer optimum,
    without needing full branch-and-price.

    Returns (patterns, counts) - the mop-up step can introduce patterns
    that weren't part of the column-generation set, so both must be
    returned together, in sync."""
    patterns = patterns.copy()
    counts = np.floor(x_fractional + 1e-9).astype(int)
    covered = counts @ patterns
    remaining_demand = np.maximum(0, problem.demand - covered)

    if remaining_demand.sum() > 0:
        remainder_problem = CuttingProblem(
            labels=problem.labels, lengths=problem.lengths,
            demand=remaining_demand, roll_length=problem.roll_length,
        )
        mopup_patterns, mopup_counts = ffd_heuristic(remainder_problem)
        for pat, cnt in zip(mopup_patterns, mopup_counts):
            match = np.where(np.all(patterns == pat, axis=1))[0]
            if len(match):
                counts[match[0]] += cnt
            else:
                patterns = np.vstack([patterns, pat])
                counts = np.append(counts, cnt)

    return patterns, counts


def ffd_heuristic(problem: CuttingProblem):
    """First-Fit-Decreasing: expand demand into individual pieces, sort
    descending by length, drop each into the first roll with room left."""
    pieces = []
    for i, (length, qty) in enumerate(zip(problem.lengths, problem.demand)):
        pieces.extend([i] * int(qty))
    pieces.sort(key=lambda i: problem.lengths[i], reverse=True)

    rolls_remaining = []  # remaining free length per open roll
    rolls_patterns = []  # piece-count vector per open roll

    for i in pieces:
        length = problem.lengths[i]
        placed = False
        for r in range(len(rolls_remaining)):
            if rolls_remaining[r] + 1e-9 >= length:
                rolls_remaining[r] -= length
                rolls_patterns[r][i] += 1
                placed = True
                break
        if not placed:
            rolls_remaining.append(problem.roll_length - length)
            new_pattern = np.zeros(problem.n_types, dtype=int)
            new_pattern[i] = 1
            rolls_patterns.append(new_pattern)

    if not rolls_patterns:
        return np.zeros((0, problem.n_types), dtype=int), np.zeros(0, dtype=int)

    # Collapse identical patterns into counts.
    unique_patterns = []
    counts = []
    for pat in rolls_patterns:
        match = next((j for j, u in enumerate(unique_patterns) if np.array_equal(u, pat)), None)
        if match is None:
            unique_patterns.append(pat)
            counts.append(1)
        else:
            counts[match] += 1

    return np.array(unique_patterns), np.array(counts, dtype=int)
