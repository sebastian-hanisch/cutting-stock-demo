"""
Ein-Klick-Beispielszenarien und Permalink-Logik - dasselbe SETTING_SPECS-
Muster wie in den anderen Demos (z. B. pack_presets.py): eine Wahrheitsquelle
für Wertebereiche, aus der sowohl der Rollenlängen-Slider als auch die
Permalink-Begrenzung lesen. Die Bestellliste hat variable Länge (ein
data_editor, keine feste Anzahl Slider) und wird deshalb separat als
kompakter "Label:Länge:Bedarf,..."-String im Permalink codiert.
"""

import math
from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd
import streamlit as st

from cutting_constants import DEFAULT_ORDERS, DEFAULT_ROLL_LENGTH, PRESETS

ORDER_COLUMNS = ["Label", "Länge (m)", "Bedarf (Stück)"]


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None


SETTING_SPECS = {
    "roll_length_slider": SettingSpec("rl", float, DEFAULT_ROLL_LENGTH, 5.0, 40.0),
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


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    if "rl" in qp:
        spec = SETTING_SPECS["roll_length_slider"]
        try:
            value = spec.caster(qp["rl"])
            if math.isfinite(value):
                st.session_state["roll_length_slider"] = max(spec.lo, min(spec.hi, value))
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
    if "roll_length_slider" not in st.session_state:
        st.session_state["roll_length_slider"] = DEFAULT_ROLL_LENGTH
    if "orders_df" not in st.session_state:
        st.session_state["orders_df"] = _orders_to_df(DEFAULT_ORDERS)


def sync_query_params(orders, roll_length):
    try:
        st.query_params["rl"] = str(roll_length)
        st.query_params["orders"] = _format_orders(orders)
    except Exception:
        pass
