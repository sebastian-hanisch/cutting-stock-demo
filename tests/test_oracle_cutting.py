"""Unabhängiges Orakel für Column Generation und FFD: vollständige Musteraufzählung + LP/ILP über
scipy (HiGHS) gegen die LP-Schranke, Zulässigkeit in exakter Ganzzahl-Arithmetik und eine eigene
FFD-Implementierung in Ganzzahlen."""

import random

import numpy as np
import pytest

from cutting_evaluation import summarize
from cutting_model import StockType, build_problem
from cutting_solver import column_generation, ffd_heuristic

optimize = pytest.importorskip("scipy.optimize")


def _patterns(lengths, cap):
    out = []

    def rec(i, rem, cur):
        if i == len(lengths):
            if any(cur):
                out.append(tuple(cur))
            return
        for a in range(rem // lengths[i] + 1):
            cur.append(a)
            rec(i + 1, rem - a * lengths[i], cur)
            cur.pop()

    rec(0, cap, [])
    return out


def _lp_and_ilp(lengths, demand, stocks):
    cols, cost = [], []
    for cap, c in stocks:
        for p in _patterns(lengths, cap):
            cols.append(p)
            cost.append(c)
    a = np.array(cols, dtype=float).T
    cost = np.array(cost)
    lp = optimize.linprog(cost, A_ub=-a, b_ub=-np.array(demand, float), bounds=(0, None), method="highs")
    ilp = optimize.milp(
        cost, constraints=optimize.LinearConstraint(a, np.array(demand, float), np.inf),
        integrality=np.ones(len(cols)), bounds=optimize.Bounds(0, np.inf),
    )
    return lp.fun, ilp.fun


def _independent_ffd_cost(lengths, demand, stocks):
    pieces = sorted((lengths[i] for i, d in enumerate(demand) for _ in range(d)), reverse=True)
    rolls, cost = [], 0.0
    for piece in pieces:
        for roll in rolls:
            if roll[0] >= piece:
                roll[0] -= piece
                break
        else:
            c, cap = min((c, cap) for cap, c in stocks if cap >= piece)
            rolls.append([cap - piece, c])
            cost += c
    return cost, len(rolls)


def _random_case(rng, decimals):
    scale = 10 ** decimals
    stocks = [(round(rng.uniform(8, 24), decimals), round(rng.uniform(3, 20), 1)) for _ in range(rng.randint(1, 3))]
    max_len = max(s[0] for s in stocks)
    orders = [
        (chr(65 + i), round(rng.uniform(1.0, min(max_len, 9.0)), decimals), rng.randint(1, 9))
        for i in range(rng.randint(1, 4))
    ]
    problem = build_problem(orders, [StockType(f"S{k}", cap, c) for k, (cap, c) in enumerate(stocks)])
    lengths = [int(round(o[1] * scale)) for o in orders]
    stocks_int = [(int(round(cap * scale)), c) for cap, c in stocks]
    return problem, lengths, [o[2] for o in orders], stocks_int


def test_column_generation_and_ffd_against_full_enumeration():
    rng = random.Random(777)
    for _ in range(80):
        problem, lengths, demand, stocks = _random_case(rng, rng.choice([1, 2]))
        lp_opt, ilp_opt = _lp_and_ilp(lengths, demand, stocks)

        cg = column_generation(problem)
        for row, k in zip(cg.patterns, cg.stock_idx):
            assert sum(int(a) * l for a, l in zip(row, lengths)) <= stocks[k][0]
        assert np.all(cg.pattern_counts @ cg.patterns >= problem.demand)
        assert cg.lp_relaxation_cost == pytest.approx(lp_opt, abs=1e-6)
        assert cg.total_cost(problem) >= ilp_opt - 1e-6

        patterns, stock_idx, counts = ffd_heuristic(problem)
        ffd_cost, ffd_rolls = _independent_ffd_cost(lengths, demand, stocks)
        assert float(np.dot(counts, [problem.stock_types[k].cost for k in stock_idx])) == pytest.approx(ffd_cost)
        assert int(counts.sum()) == ffd_rolls
        assert ffd_cost >= ilp_opt - 1e-6

        for pat, idx, cnt in ((patterns, stock_idx, counts), (cg.patterns, cg.stock_idx, cg.pattern_counts)):
            summary = summarize(problem, pat, idx, cnt)
            stock_total = sum(c * stocks[k][0] for c, k in zip(cnt, idx))
            cut = sum(c * sum(int(a) * l for a, l in zip(p, lengths)) for p, c in zip(pat, cnt))
            over = max(0, cut - sum(d * l for d, l in zip(demand, lengths)))
            assert summary.waste_pct == pytest.approx(100.0 * (stock_total - cut + over) / stock_total, abs=1e-6)


def test_pricing_never_builds_pattern_longer_than_the_roll_for_sub_centimetre_inputs():
    # 3 x 3,334 m = 10,002 m passt NICHT auf eine 10-m-Rolle; auf Zentimeter gerundet (3,33 m) sähe es so aus.
    problem = build_problem([("A", 3.334, 6)], [StockType("Standard", 10.0, 1.0)])
    result = column_generation(problem)
    for row, k in zip(result.patterns, result.stock_idx):
        assert float(np.dot(row, problem.lengths)) <= problem.stock_types[k].length + 1e-9
    assert result.total_rolls == 3  # höchstens 2 Stück je Rolle -> 3 Rollen für 6 Stück
    assert np.all(result.pattern_counts @ result.patterns >= problem.demand)
