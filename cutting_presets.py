"""
Ein-Klick-Beispielszenarien und Permalink-Logik - dasselbe SETTING_SPECS-
Muster wie in den anderen Demos (z. B. pack_presets.py): eine Wahrheitsquelle
für Wertebereiche, aus der sowohl die Slider als auch die Permalink-
Begrenzung lesen. Sowohl die Bestellliste als auch der Rollenkatalog haben
variable Länge (zwei data_editor-Tabellen, keine feste Anzahl Slider) und
werden deshalb separat als kompakte "Label:Wert:Wert,..."-Strings im
Permalink codiert.
"""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd
import streamlit as st

from cutting_constants import DEFAULT_N_TYPES, DEFAULT_ORDERS, DEFAULT_SEED, DEFAULT_STOCK_TYPES, PRESETS
from cutting_model import StockType

ORDER_COLUMNS = ["Label", "Länge (m)", "Bedarf (Stück)"]
STOCK_COLUMNS = ["Label", "Länge (m)", "Kosten (€)"]
ORDER_LABELS = "ABCDEFGHIJ"


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None


SETTING_SPECS = {
    "n_types_slider": SettingSpec("n_types", int, DEFAULT_N_TYPES, 2, len(ORDER_LABELS)),
    "seed_input": SettingSpec("seed", int, DEFAULT_SEED, 0, 2_000_000_000),
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def _orders_to_df(orders):
    return pd.DataFrame(orders, columns=ORDER_COLUMNS)


def _stock_to_df(stock_types):
    rows = [(s.label, s.length, s.cost) if isinstance(s, StockType) else s for s in stock_types]
    return pd.DataFrame(rows, columns=STOCK_COLUMNS)


def stock_types_from_df(stock_df) -> tuple:
    return tuple(
        StockType(str(row["Label"]), float(row["Länge (m)"]), float(row["Kosten (€)"]))
        for _, row in stock_df.dropna().iterrows()
        if float(row["Länge (m)"]) > 0
    )


def _parse_orders(v):
    orders = []
    for part in v.split(","):
        if not part.strip():
            continue
        label, length, demand = part.split(":")
        orders.append((label, float(length), int(demand)))
    return orders


def _format_orders(orders):
    return ",".join(f"{label}:{length:g}:{int(demand)}" for label, length, demand in orders)


def _parse_stock(v):
    stock = []
    for part in v.split(","):
        if not part.strip():
            continue
        label, length, cost = part.split(":")
        stock.append((label, float(length), float(cost)))
    return stock


def _format_stock(stock_types):
    parts = []
    for s in stock_types:
        label, length, cost = (s.label, s.length, s.cost) if isinstance(s, StockType) else s
        parts.append(f"{label}:{length:g}:{cost:g}")
    return ",".join(parts)


def apply_preset(name):
    cfg = PRESETS[name]
    st.session_state["stock_df"] = _stock_to_df(cfg["stock_types"])
    st.session_state["orders_df"] = _orders_to_df(cfg["orders"])


def generate_random_orders(seed: int, n_types: int, max_length: float) -> list:
    """Random order book: piece lengths as a random fraction of the longest
    available stock type (15-65 %, so pieces are neither trivially small nor
    forced into a single-item pattern), random demand per type."""
    rng = np.random.default_rng(int(seed))
    lengths = np.round(rng.uniform(0.15, 0.65, size=n_types) * max_length, 1)
    demand = rng.integers(5, 26, size=n_types)
    return [(ORDER_LABELS[i], float(lengths[i]), int(demand[i])) for i in range(n_types)]


def randomize_orders():
    """on_click-Callback für den 'Zufällige Bestellung generieren'-Button.
    Würfelt bei jedem Klick selbst einen neuen Seed (nicht nur den aktuell
    im Feld stehenden Wert erneut verwenden) - sonst bewirkt ein Klick ohne
    zusätzliche manuelle Seed-Änderung sichtbar gar nichts, derselbe Fehler
    wie bei den analogen Buttons in den anderen Demos (siehe dortige
    Historie, z. B. pack_presets.py)."""
    seed = random.randint(0, 2_000_000_000)
    st.session_state["seed_input"] = seed
    n_types = st.session_state.get("n_types_slider", DEFAULT_N_TYPES)
    stock_df = st.session_state.get("stock_df", _stock_to_df(DEFAULT_STOCK_TYPES))
    stock_types = stock_types_from_df(stock_df) or DEFAULT_STOCK_TYPES
    max_length = max(s.length for s in stock_types)
    st.session_state["orders_df"] = _orders_to_df(generate_random_orders(seed, n_types, max_length))


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
                if isinstance(value, float) and not math.isfinite(value):
                    continue
                if spec.lo is not None:
                    value = max(spec.lo, value)
                if spec.hi is not None:
                    value = min(spec.hi, value)
                st.session_state[state_key] = value
            except (ValueError, TypeError):
                pass
    if "orders" in qp:
        try:
            orders = _parse_orders(qp["orders"])
            if orders:
                st.session_state["orders_df"] = _orders_to_df(orders)
        except (ValueError, TypeError):
            pass
    if "stock" in qp:
        try:
            stock = _parse_stock(qp["stock"])
            if stock:
                st.session_state["stock_df"] = _stock_to_df(stock)
        except (ValueError, TypeError):
            pass
    st.session_state["permalink_loaded"] = True


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default
    if "orders_df" not in st.session_state:
        st.session_state["orders_df"] = _orders_to_df(DEFAULT_ORDERS)
    if "stock_df" not in st.session_state:
        st.session_state["stock_df"] = _stock_to_df(DEFAULT_STOCK_TYPES)


def sync_query_params(orders, stock_types, n_types, seed):
    try:
        st.query_params["n_types"] = str(n_types)
        st.query_params["seed"] = str(int(seed))
        st.query_params["orders"] = _format_orders(orders)
        st.query_params["stock"] = _format_stock(stock_types)
    except Exception:
        pass
