import numpy as np

from cutting_model import build_problem, is_feasible_pattern, trivial_patterns


def test_build_problem_basic():
    problem = build_problem([("A", 6.0, 5), ("B", 4.0, 5)], roll_length=10.0)
    assert problem.labels == ("A", "B")
    assert np.array_equal(problem.lengths, [6.0, 4.0])
    assert np.array_equal(problem.demand, [5, 5])
    assert problem.n_types == 2


def test_trivial_patterns_are_feasible_and_cover_each_type():
    problem = build_problem([("A", 6.0, 5), ("B", 4.0, 5)], roll_length=10.0)
    patterns = trivial_patterns(problem)
    assert patterns.shape == (2, 2)
    for row in patterns:
        assert is_feasible_pattern(row, problem.lengths, problem.roll_length)
    # Pattern i must contain at least one unit of item i (otherwise it
    # couldn't help cover that item's demand at all).
    for i in range(problem.n_types):
        assert patterns[i, i] >= 1


def test_infeasible_pattern_detected():
    lengths = np.array([6.0, 4.0])
    # Two of item 0 (6+6=12) does not fit in a roll of length 10.
    assert not is_feasible_pattern(np.array([2, 0]), lengths, roll_length=10.0)
