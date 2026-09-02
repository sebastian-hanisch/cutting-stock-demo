"""
Ein-Klick-Beispielszenarien und Permalink-Logik - dasselbe SETTING_SPECS-
Muster wie in den anderen Demos (z. B. pack_presets.py): eine Wahrheitsquelle
für Wertebereiche, aus der sowohl der Rollenlängen-Slider als auch die
Permalink-Begrenzung lesen. Die Bestellliste hat variable Länge (ein
data_editor, keine feste Anzahl Slider) und wird deshalb separat als
kompakter "Label:Länge:Bedarf,..."-String im Permalink codiert.
"""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd
import streamlit as st

from cutting_constants import DEFAULT_N_TYPES, DEFAULT_ORDERS, DEFAULT_ROLL_LENGTH, DEFAULT_SEED, PRESETS

ORDER_COLUMNS = ["Label", "Länge (m)", "Bedarf (Stück)"]
ORDER_LABELS = "ABCDEFGHIJ"


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None


SETTING_SPECS = {
    "roll_length_slider": SettingSpec("rl", float, DEFAULT_ROLL_LENGTH, 5.0, 40.0),
    "n_types_slider": SettingSpec("n_types", int, DEFAULT_N_TYPES, 2, len(ORDER_LABELS)),
    "seed_input": SettingSpec("seed", int, DEFAULT_SEED, 0, 2_000_000_000),
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def _orders_to_df(orders):
    return pd.DataFrame(orders, columns=ORDER_COLUMNS)


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


def apply_preset(name):
    cfg = PRESETS[name]
    st.session_state["roll_length_slider"] = cfg["roll_length"]
    st.session_state["orders_df"] = _orders_to_df(cfg["orders"])


def generate_random_orders(seed: int, n_types: int, roll_length: float) -> list:
    """Random order book: piece lengths as a random fraction of the roll
    length (15-65 %, so pieces are neither trivially small nor forced into
    a single-item pattern), random demand per type."""
    rng = np.random.default_rng(int(seed))
    lengths = np.round(rng.uniform(0.15, 0.65, size=n_types) * roll_length, 1)
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
    roll_length = st.session_state.get("roll_length_slider", DEFAULT_ROLL_LENGTH)
    st.session_state["orders_df"] = _orders_to_df(generate_random_orders(seed, n_types, roll_length))


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
    st.session_state["permalink_loaded"] = True


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default
    if "orders_df" not in st.session_state:
        st.session_state["orders_df"] = _orders_to_df(DEFAULT_ORDERS)


def sync_query_params(orders, roll_length, n_types, seed):
    try:
        st.query_params["rl"] = str(roll_length)
        st.query_params["n_types"] = str(n_types)
        st.query_params["seed"] = str(int(seed))
        st.query_params["orders"] = _format_orders(orders)
    except Exception:
        pass
