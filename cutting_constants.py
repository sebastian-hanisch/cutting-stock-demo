"""Sample data and presets for the cutting-stock demo."""

from cutting_model import StockType

# Standard stock catalog: several available roll lengths at different costs
# (e.g. steel bar, cable drum, paper roll stock) - longer rolls cost less per
# meter (economies of scale), but only pay off if a pattern can actually use
# the extra length.
DEFAULT_STOCK_TYPES = (
    StockType("Kurz (12 m)", 12.0, 8.5),
    StockType("Standard (20 m)", 20.0, 14.0),
    StockType("Lang (30 m)", 30.0, 20.0),
)

DEFAULT_SEED = 42
DEFAULT_N_TYPES = 4

# A modest, realistic order book - shown under the "Standard-Sortiment" preset.
STANDARD_ORDERS = [
    ("A", 13.0, 10),
    ("B", 7.0, 10),
    ("C", 6.0, 10),
    ("D", 4.0, 10),
]

# Every single piece (~5 m) comfortably fits the cheapest stock type (Kurz,
# 12 m) alone, so FFD's "cheapest that fits" rule pairs two same-type pieces
# per Kurz roll and never looks further - it has no way to notice that one
# of each of the six types sums to exactly 30 m, a perfect zero-waste fit
# for a single (pricier per roll, but much cheaper per meter) Lang roll.
# Column generation's pricing step finds that combined pattern immediately:
# ~22 % cheaper, and provably optimal (LP bound == integer solution). This
# is what the app loads on first visit (and what sebastianhanisch.net links
# to) precisely because it's the clearest demonstration of the difference -
# the "Standard-Sortiment" preset button is still there for the more modest,
# everyday case.
DEFAULT_ORDERS = [
    ("A", 5.2, 12), ("B", 5.1, 12), ("C", 5.0, 12),
    ("D", 4.95, 12), ("E", 4.9, 12), ("F", 4.85, 12),
]

# Presets swap in a different stock catalog and/or order book.
PRESETS = {
    "Worst Case für FFD": {
        "stock_types": DEFAULT_STOCK_TYPES,
        "orders": DEFAULT_ORDERS,
    },
    "Standard-Sortiment": {
        "stock_types": DEFAULT_STOCK_TYPES,
        "orders": STANDARD_ORDERS,
    },
    "Wenige, lange Stücke": {
        "stock_types": DEFAULT_STOCK_TYPES,
        "orders": [("A", 25.0, 6), ("B", 14.0, 8), ("C", 9.0, 10)],
    },
    "Viele, kurze Stücke": {
        "stock_types": DEFAULT_STOCK_TYPES,
        "orders": [
            ("A", 3.2, 20), ("B", 2.8, 24), ("C", 2.3, 28),
            ("D", 1.9, 30), ("E", 1.5, 34), ("F", 1.1, 36),
        ],
    },
}
