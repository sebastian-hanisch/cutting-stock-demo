import numpy as np

from cutting_model import build_problem, is_feasible_pattern
from cutting_solver import column_generation, ffd_heuristic


def _assert_feasible_and_sufficient(problem, patterns, counts):
    for row in patterns:
        assert is_feasible_pattern(row, problem.lengths, problem.roll_length)
    produced = counts @ patterns
    assert np.all(produced >= problem.demand), (produced, problem.demand)


def test_single_item_type_needs_ceil_division_rolls():
    # roll=10, item length 3, demand 7: each roll fits 3 (9 used, 1 wasted),
    # so ceil(7/3) = 3 rolls is provably optimal - no pattern can beat 3 per
    # roll for a single item type, and 2 rolls could cover at most 6 < 7.
    problem = build_problem([("A", 3.0, 7)], roll_length=10.0)
    result = column_generation(problem)
    _assert_feasible_and_sufficient(problem, result.patterns, result.pattern_counts)
    assert result.total_rolls == 3


def test_column_generation_finds_combined_pattern_ffd_cannot():
    # roll=10, item A=6 (demand 5), item B=4 (demand 5). A mixed pattern
    # [1 A, 1 B] uses exactly 10 with zero waste, so 5 rolls suffice and are
    # provably optimal (>=5 rolls are needed regardless, since each roll
    # holds at most one A and 5 A's must be covered). Using only "trivial"
    # single-item patterns needs 5 + ceil(5/2) = 8 rolls - so this instance
    # specifically tests that column generation's pricing step actually
    # discovers the combined pattern instead of settling for trivial ones.
    problem = build_problem([("A", 6.0, 5), ("B", 4.0, 5)], roll_length=10.0)
    result = column_generation(problem)
    _assert_feasible_and_sufficient(problem, result.patterns, result.pattern_counts)
    assert result.total_rolls == 5
    assert any(np.array_equal(p, [1, 1]) for p in result.patterns)


def test_lp_relaxation_is_a_valid_lower_bound():
    problem = build_problem([("A", 6.0, 5), ("B", 4.0, 5)], roll_length=10.0)
    result = column_generation(problem)
    assert result.lp_relaxation_rolls <= result.total_rolls + 1e-6


def test_ffd_is_feasible():
    problem = build_problem([("A", 7.0, 12), ("B", 5.5, 15), ("C", 4.5, 18)], roll_length=20.0)
    patterns, counts = ffd_heuristic(problem)
    _assert_feasible_and_sufficient(problem, patterns, counts)


def test_column_generation_never_worse_than_ffd_on_default_scenario():
    from cutting_constants import DEFAULT_ORDERS, DEFAULT_ROLL_LENGTH

    problem = build_problem(DEFAULT_ORDERS, roll_length=DEFAULT_ROLL_LENGTH)
    cg_result = column_generation(problem)
    _, ffd_counts = ffd_heuristic(problem)
    assert cg_result.total_rolls <= int(ffd_counts.sum())
