"""Comparison metrics between the two solution methods."""

from dataclasses import dataclass

import numpy as np

from cutting_model import CuttingProblem


@dataclass
class SolutionSummary:
    total_rolls: int
    total_cost: float  # sum of the cost of every roll actually bought - the real objective
    cut_length: float  # total length actually cut across all patterns - can exceed demand_length
    demand_length: float  # true ordered length, sum(length_i * demand_i) - identical for any valid solution
    overproduction_length: float  # cut_length beyond demand_length: pieces cut but never ordered
    trim_length: float  # physical leftover inside rolls that was never cut at all
    waste_length: float  # trim_length + overproduction_length: everything that didn't go to the order
    waste_pct: float


def summarize(problem: CuttingProblem, patterns: np.ndarray, stock_idx: np.ndarray, counts: np.ndarray) -> SolutionSummary:
    """FFD only ever cuts exactly the ordered piece counts, but column
    generation's master problem is a covering LP (>= demand, not = demand)
    and its rounding step can round certain patterns up past what was
    actually ordered. Counting that overproduced length as "waste" (like
    trim, it isn't material the customer gets) keeps the two methods'
    waste_pct comparable - counting it as "used" would understate CG's true
    material cost relative to FFD, which never overproduces."""
    total_rolls = int(counts.sum())
    stock_lengths = np.array([problem.stock_types[k].length for k in stock_idx])
    stock_costs = np.array([problem.stock_types[k].cost for k in stock_idx])
    total_cost = float(np.dot(counts, stock_costs))
    total_stock_length = float(np.dot(counts, stock_lengths))
    cut_length = float(sum(c * np.dot(pat, problem.lengths) for pat, c in zip(patterns, counts)))
    demand_length = float(np.dot(problem.demand, problem.lengths))
    overproduction_length = max(0.0, cut_length - demand_length)
    trim_length = max(0.0, total_stock_length - cut_length)
    waste_length = trim_length + overproduction_length
    waste_pct = 100.0 * waste_length / total_stock_length if total_stock_length > 0 else 0.0
    return SolutionSummary(
        total_rolls=total_rolls,
        total_cost=total_cost,
        cut_length=cut_length,
        demand_length=demand_length,
        overproduction_length=overproduction_length,
        trim_length=trim_length,
        waste_length=waste_length,
        waste_pct=waste_pct,
    )


def equal_cost_note(cg_cost: float, lp_cost: float) -> str:
    """Text für den Fall 'FFD und Column Generation kosten gleich viel'. Bewiesen ist nur die LP-Schranke als untere
    Grenze für jede ganzzahlige Lösung; erst wenn die Lösungskosten sie erreichen, ist die Lösung nachweislich optimal."""
    head = "In diesem Szenario erreicht die einfache FFD-Heuristik zufällig bereits dieselben Kosten wie Column Generation. "
    if cg_cost - lp_cost <= 1e-6:
        body = (
            "Die Kosten liegen auf der LP-Schranke, und keine ganzzahlige Lösung kann unter dieser Schranke liegen: "
            "Beide Lösungen sind damit nachweislich optimal."
        )
    else:
        body = (
            f"Bewiesen ist nur die LP-Schranke ({lp_cost:.2f} €): Keine ganzzahlige Lösung kann günstiger sein. "
            f"Die Lösung von Column Generation kostet {cg_cost:.2f} € und liegt darüber; ob eine ganzzahlige Lösung "
            f"zwischen Schranke und {cg_cost:.2f} € existiert, folgt aus der Schranke allein nicht. "
        )
    tail = " Probieren Sie ein anderes Szenario oder eigene Bestellungen/Rollentypen aus, um einen Fall zu sehen, in dem FFD tatsächlich mehr kostet."
    return head + body.rstrip() + tail
