"""Two solution approaches for the 1D cutting-stock problem with multiple
available stock lengths/costs, compared head to head in the demo:

1. First-Fit-Decreasing (FFD): a naive, fast bin-packing heuristic. Sorts all
   individual pieces by length descending and drops each one into the first
   open roll with enough room left. Only when none fits does it open a new
   roll - and since real suppliers stock several standard lengths at
   different prices, it has to decide *which* stock type to open, too. It
   does this the way a non-optimizing operator would: grab the cheapest
   stock type that is long enough for the piece in hand. That is a purely
   local decision with no view of the rest of the order book.

2. Column generation: rather than enumerating every possible (stock type,
   cutting pattern) combination up front, it starts from a handful of
   trivial patterns, solves the LP relaxation of the "pick a minimum-cost
   mix of patterns" master problem, and uses that solution's dual (shadow)
   prices to guide one small knapsack subproblem per stock type toward the
   single most valuable *new* pattern to add next. Repeats until no pattern
   would improve the relaxation - at that point the LP relaxation is
   provably optimal for the *fractional* problem, and is usually within a
   roll or two of the true integer optimum. Because pricing runs once per
   stock type every iteration, column generation always weighs the same
   cost-per-piece trade-off across *all* stock types at once - exactly the
   global view FFD's "cheapest that fits" rule cannot take. The fractional
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
    stock_idx: np.ndarray  # shape (n_patterns,), index into problem.stock_types per pattern
    pattern_counts: np.ndarray  # integer number of rolls cut to each pattern, shape (n_patterns,)
    lp_relaxation_cost: float  # fractional LP objective - a valid lower bound on any integer solution's cost
    iterations: int
    iteration_log: list = field(default_factory=list)  # one entry per CG iteration, for the explainer

    def costs(self, problem: CuttingProblem) -> np.ndarray:
        return np.array([problem.stock_types[k].cost for k in self.stock_idx])

    @property
    def total_rolls(self) -> int:
        return int(self.pattern_counts.sum())

    def total_cost(self, problem: CuttingProblem) -> float:
        return float(np.dot(self.pattern_counts, self.costs(problem)))


def _knapsack_pricing(lengths: np.ndarray, prices: np.ndarray, capacity_length: float, resolution: float = 0.01):
    """Solve max sum(price_i * a_i) s.t. sum(length_i * a_i) <= capacity_length,
    a_i >= 0 integer - the column-generation pricing subproblem for one
    stock type. This is an unbounded knapsack, solved by exact DP over the
    (discretized) capacity. `resolution` is the unit lengths are rounded to
    (e.g. 0.01 = cm precision for meter-scale inputs) so the DP can use
    integer capacities.
    """
    capacity = int(round(capacity_length / resolution))
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
    patterns, stock_idx = trivial_patterns(problem)
    costs = np.array([problem.stock_types[k].cost for k in stock_idx])
    log = []

    for iteration in range(max_iterations):
        n_patterns = patterns.shape[0]
        # Master LP: minimize sum(costs[j] * x_j) s.t. patterns.T @ x >= demand, x >= 0.
        # linprog only does <=, so negate to flip the inequality direction.
        A_ub = -patterns.T
        b_ub = -problem.demand
        res = linprog(costs, A_ub=A_ub, b_ub=b_ub, bounds=(0, None), method="highs")
        if not res.success:
            raise RuntimeError(f"Master LP failed: {res.message}")

        # scipy's marginals are d(objective)/d(b_ub); since b_ub = -demand,
        # the dual price for the original >= constraint is the negative of
        # that (increasing demand can only ever raise cost, so this price
        # is >= 0 for a sensible cutting-stock instance).
        dual_prices = -res.ineqlin.marginals

        # Pricing runs once per stock type - the new column is whichever
        # (stock type, pattern) pair improves the master problem the most.
        best_k, best_pattern, best_reduced_cost, best_value = None, None, np.inf, None
        for k, stock in enumerate(problem.stock_types):
            candidate_pattern, value = _knapsack_pricing(problem.lengths, dual_prices, stock.length, resolution)
            reduced_cost = stock.cost - value
            if reduced_cost < best_reduced_cost:
                best_k, best_pattern, best_reduced_cost, best_value = k, candidate_pattern, reduced_cost, value

        log.append({
            "iteration": iteration,
            "lp_cost": float(res.fun),
            "reduced_cost": best_reduced_cost,
            "new_pattern": best_pattern.copy(),
            "new_stock_type": problem.stock_types[best_k].label,
        })

        already_present = np.any((stock_idx == best_k) & np.all(patterns == best_pattern, axis=1))
        if best_reduced_cost >= -tol or already_present:
            final_patterns, final_stock_idx, final_counts = _round_lp_solution(problem, patterns, stock_idx, res.x)
            return ColumnGenerationResult(
                patterns=final_patterns,
                stock_idx=final_stock_idx,
                pattern_counts=final_counts,
                lp_relaxation_cost=float(res.fun),
                iterations=iteration + 1,
                iteration_log=log,
            )

        patterns = np.vstack([patterns, best_pattern])
        stock_idx = np.append(stock_idx, best_k)
        costs = np.append(costs, problem.stock_types[best_k].cost)

    raise RuntimeError("Column generation did not converge within max_iterations")


def _round_lp_solution(problem: CuttingProblem, patterns: np.ndarray, stock_idx: np.ndarray, x_fractional: np.ndarray):
    """Round the fractional LP solution to an integer one: keep the full
    rolls of each pattern (floor), then use FFD to mop up whatever demand
    the fractional remainder didn't cover. This is a standard, simple
    cutting-stock rounding scheme - it stays feasible by construction and
    empirically lands within a roll or two of the true integer optimum,
    without needing full branch-and-price.

    Returns (patterns, stock_idx, counts) - the mop-up step can introduce
    patterns that weren't part of the column-generation set, so all three
    must be returned together, in sync."""
    patterns = patterns.copy()
    stock_idx = stock_idx.copy()
    counts = np.floor(x_fractional + 1e-9).astype(int)
    covered = counts @ patterns
    remaining_demand = np.maximum(0, problem.demand - covered)

    if remaining_demand.sum() > 0:
        remainder_problem = CuttingProblem(
            labels=problem.labels, lengths=problem.lengths,
            demand=remaining_demand, stock_types=problem.stock_types,
        )
        mopup_patterns, mopup_stock_idx, mopup_counts = ffd_heuristic(remainder_problem)
        for pat, k, cnt in zip(mopup_patterns, mopup_stock_idx, mopup_counts):
            match = np.where((stock_idx == k) & np.all(patterns == pat, axis=1))[0]
            if len(match):
                counts[match[0]] += cnt
            else:
                patterns = np.vstack([patterns, pat])
                stock_idx = np.append(stock_idx, k)
                counts = np.append(counts, cnt)

    return patterns, stock_idx, counts


def ffd_heuristic(problem: CuttingProblem):
    """First-Fit-Decreasing: expand demand into individual pieces, sort
    descending by length, drop each into the first open roll with room
    left. When none fits, open a new roll of the cheapest stock type long
    enough for the piece (ties broken by shortest such type) - a purely
    local, non-optimizing choice."""
    pieces = []
    for i, (length, qty) in enumerate(zip(problem.lengths, problem.demand)):
        pieces.extend([i] * int(qty))
    pieces.sort(key=lambda i: problem.lengths[i], reverse=True)

    rolls_remaining = []  # remaining free length per open roll
    rolls_patterns = []  # piece-count vector per open roll
    rolls_stock_idx = []  # stock type index per open roll

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
            candidates = [k for k, s in enumerate(problem.stock_types) if s.length >= length]
            k = min(candidates, key=lambda k: (problem.stock_types[k].cost, problem.stock_types[k].length))
            rolls_remaining.append(problem.stock_types[k].length - length)
            new_pattern = np.zeros(problem.n_types, dtype=int)
            new_pattern[i] = 1
            rolls_patterns.append(new_pattern)
            rolls_stock_idx.append(k)

    if not rolls_patterns:
        return np.zeros((0, problem.n_types), dtype=int), np.zeros(0, dtype=int), np.zeros(0, dtype=int)

    # Collapse identical (pattern, stock type) combinations into counts.
    unique_patterns = []
    unique_stock_idx = []
    counts = []
    for pat, k in zip(rolls_patterns, rolls_stock_idx):
        match = next(
            (j for j, (u, uk) in enumerate(zip(unique_patterns, unique_stock_idx)) if uk == k and np.array_equal(u, pat)),
            None,
        )
        if match is None:
            unique_patterns.append(pat)
            unique_stock_idx.append(k)
            counts.append(1)
        else:
            counts[match] += 1

    return np.array(unique_patterns), np.array(unique_stock_idx, dtype=int), np.array(counts, dtype=int)
