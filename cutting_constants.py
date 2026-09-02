"""Sample data and presets for the cutting-stock demo."""

# Standard stock length in meters (e.g. a steel bar, cable drum, paper roll).
DEFAULT_ROLL_LENGTH = 20.0

# A representative order book: (label, piece length in meters, demand in pieces).
# Verified to give column generation a real, if modest, edge over FFD:
# 15 vs. 16 rolls (see tests/test_solver.py for the CG<=FFD check).
DEFAULT_ORDERS = [
    ("A", 13.0, 10),
    ("B", 7.0, 10),
    ("C", 6.0, 10),
    ("D", 4.0, 10),
]

# Presets swap in a different order book to show the effect on the CG/FFD gap.
PRESETS = {
    "Standard-Sortiment": {
        "roll_length": 20.0,
        "orders": DEFAULT_ORDERS,
    },
    "Wenige, lange Stücke": {
        "roll_length": 20.0,
        "orders": [("A", 11.0, 10), ("B", 9.0, 10), ("C", 6.5, 10)],
    },
    "Viele, kurze Stücke": {
        "roll_length": 20.0,
        "orders": [
            ("A", 3.2, 20), ("B", 2.8, 24), ("C", 2.3, 28),
            ("D", 1.9, 30), ("E", 1.5, 34), ("F", 1.1, 36),
        ],
    },
}
