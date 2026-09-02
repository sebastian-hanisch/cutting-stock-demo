import numpy as np

from cutting_model import StockType, build_problem, is_feasible_pattern
from cutting_solver import column_generation, ffd_heuristic


def _assert_feasible_and_sufficient(problem, patterns, stock_idx, counts):
    for row, k in zip(patterns, stock_idx):
        assert is_feasible_pattern(row, problem.lengths, problem.stock_types[k].length)
    produced = counts @ patterns
    assert np.all(produced >= problem.demand), (produced, problem.demand)


def test_single_item_type_needs_ceil_division_rolls():
    # stock=10, item length 3, demand 7: each roll fits 3 (9 used, 1 wasted),
    # so ceil(7/3) = 3 rolls is provably optimal - no pattern can beat 3 per
    # roll for a single item type, and 2 rolls could cover at most 6 < 7.
    stock_types = (StockType("Standard", 10.0, 1.0),)
    problem = build_problem([("A", 3.0, 7)], stock_types)
    result = column_generation(problem)
    _assert_feasible_and_sufficient(problem, result.patterns, result.stock_idx, result.pattern_counts)
    assert result.total_rolls == 3


def test_column_generation_finds_combined_pattern_ffd_cannot():
    # stock=10, item A=6 (demand 5), item B=4 (demand 5). A mixed pattern
    # [1 A, 1 B] uses exactly 10 with zero waste, so 5 rolls suffice and are
    # provably optimal (>=5 rolls are needed regardless, since each roll
    # holds at most one A and 5 A's must be covered). Using only "trivial"
    # single-item patterns needs 5 + ceil(5/2) = 8 rolls - so this instance
    # specifically tests that column generation's pricing step actually
    # discovers the combined pattern instead of settling for trivial ones.
    stock_types = (StockType("Standard", 10.0, 1.0),)
    problem = build_problem([("A", 6.0, 5), ("B", 4.0, 5)], stock_types)
    result = column_generation(problem)
    _assert_feasible_and_sufficient(problem, result.patterns, result.stock_idx, result.pattern_counts)
    assert result.total_rolls == 5
    assert any(np.array_equal(p, [1, 1]) for p in result.patterns)


def test_lp_relaxation_is_a_valid_lower_bound():
    stock_types = (StockType("Standard", 10.0, 1.0),)
    problem = build_problem([("A", 6.0, 5), ("B", 4.0, 5)], stock_types)
    result = column_generation(problem)
    assert result.lp_relaxation_cost <= result.total_cost(problem) + 1e-6


def test_ffd_is_feasible():
    stock_types = (StockType("Standard", 20.0, 1.0),)
    problem = build_problem([("A", 7.0, 12), ("B", 5.5, 15), ("C", 4.5, 18)], stock_types)
    patterns, stock_idx, counts = ffd_heuristic(problem)
    _assert_feasible_and_sufficient(problem, patterns, stock_idx, counts)


def test_column_generation_never_worse_than_ffd_on_default_scenario():
    from cutting_constants import DEFAULT_ORDERS, DEFAULT_STOCK_TYPES

    problem = build_problem(DEFAULT_ORDERS, DEFAULT_STOCK_TYPES)
    cg_result = column_generation(problem)
    _, ffd_stock_idx, ffd_counts = ffd_heuristic(problem)
    ffd_cost = sum(c * problem.stock_types[k].cost for c, k in zip(ffd_counts, ffd_stock_idx))
    assert cg_result.total_cost(problem) <= ffd_cost + 1e-6


def test_column_generation_beats_ffd_cost_with_multiple_stock_types():
    # FFD's "cheapest stock type that fits this one piece" rule opens many
    # small/medium rolls piece by piece and never discovers that A+B+C+D
    # combine into exactly one Lang roll with zero waste - column generation
    # searches all stock types via its pricing subproblem and finds it.
    orders = [("A", 13.0, 10), ("B", 7.0, 10), ("C", 6.0, 10), ("D", 4.0, 10)]
    stock_types = (StockType("Kurz", 12.0, 8.5), StockType("Standard", 20.0, 14.0), StockType("Lang", 30.0, 20.0))
    problem = build_problem(orders, stock_types)
    cg_result = column_generation(problem)
    _, ffd_stock_idx, ffd_counts = ffd_heuristic(problem)
    ffd_cost = sum(c * problem.stock_types[k].cost for c, k in zip(ffd_counts, ffd_stock_idx))
    assert cg_result.total_cost(problem) < ffd_cost
