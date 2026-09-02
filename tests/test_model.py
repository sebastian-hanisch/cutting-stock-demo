import numpy as np

from cutting_model import StockType, build_problem, is_feasible_pattern, trivial_patterns


def test_build_problem_basic():
    stock_types = (StockType("Standard", 10.0, 5.0),)
    problem = build_problem([("A", 6.0, 5), ("B", 4.0, 5)], stock_types)
    assert problem.labels == ("A", "B")
    assert np.array_equal(problem.lengths, [6.0, 4.0])
    assert np.array_equal(problem.demand, [5, 5])
    assert problem.n_types == 2
    assert problem.max_stock_length == 10.0


def test_trivial_patterns_are_feasible_and_cover_each_type():
    stock_types = (StockType("Standard", 10.0, 5.0),)
    problem = build_problem([("A", 6.0, 5), ("B", 4.0, 5)], stock_types)
    patterns, stock_idx = trivial_patterns(problem)
    assert patterns.shape == (2, 2)
    for row, k in zip(patterns, stock_idx):
        assert is_feasible_pattern(row, problem.lengths, problem.stock_types[k].length)
    # Pattern i must contain at least one unit of item i (otherwise it
    # couldn't help cover that item's demand at all).
    for i in range(problem.n_types):
        assert patterns[i, i] >= 1


def test_trivial_patterns_pick_shortest_sufficient_stock_type():
    # A 6m piece fits both stock types - the trivial pattern should still
    # pick the shorter one (Kurz), since that's enough to bootstrap a
    # feasible restricted master problem without wasting the choice on the
    # unnecessarily long/expensive one.
    stock_types = (StockType("Kurz", 8.0, 4.0), StockType("Lang", 20.0, 9.0))
    problem = build_problem([("A", 6.0, 5)], stock_types)
    _, stock_idx = trivial_patterns(problem)
    assert stock_idx[0] == 0


def test_infeasible_pattern_detected():
    lengths = np.array([6.0, 4.0])
    # Two of item 0 (6+6=12) does not fit a stock length of 10.
    assert not is_feasible_pattern(np.array([2, 0]), lengths, stock_length=10.0)
