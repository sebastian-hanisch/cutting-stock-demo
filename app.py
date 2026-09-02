"""
Zuschnittoptimierung (Cutting Stock Problem) - interaktive Demo
Sebastian Hanisch - Operations Research und Machine Learning

Ein Lieferant führt mehrere Standard-Rollenlängen (Stahl, Kabel, Papier) zu
unterschiedlichen Kosten, aus denen bestellte Zuschnittlängen zerlegt werden
sollen - mit möglichst geringen Gesamtkosten. Diese Demo vergleicht zwei
Lösungswege:

- First-Fit-Decreasing (FFD): eine schnelle, naive Greedy-Heuristik. Öffnet
  eine neue Rolle immer mit dem billigsten Rollentyp, der für das aktuelle
  Stück reicht - eine rein lokale Entscheidung ohne Blick auf die restliche
  Bestellung.
- Column Generation: löst iterativ die LP-Relaxierung eines "wähle die
  guenstigste Mischung aus Schnittmustern"-Modells, ohne je alle möglichen
  Muster aufzählen zu müssen (bei realistischen Bestellungen praktisch
  unzählbar viele) - die Dualwerte der LP-Lösung steuern je ein kleines
  Rucksack-Teilproblem pro Rollentyp, das jeweils genau das eine wertvollste
  neue Muster liefert. Die LP-Relaxierung liefert außerdem eine mathematisch
  bewiesene untere Kostenschranke: eine Garantie, wie nah jede Lösung
  höchstens am Optimum liegen kann - etwas, das eine reine Heuristik nie
  liefern kann.

Code-Struktur wie bei den anderen Demos in diesem Workspace: Modell, Solver
und Visualisierung liegen in eigenen cutting_*.py-Modulen neben dieser Datei.
"""

import streamlit as st

from cutting_constants import PRESETS
from cutting_evaluation import summarize
from cutting_model import build_problem
from cutting_pdf_export import generate_cutting_report_pdf
from cutting_presets import (
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_orders,
    stock_types_from_df,
    sync_query_params,
)
from cutting_solver import column_generation, ffd_heuristic
from cutting_visualization import pattern_figure

st.set_page_config(page_title="Zuschnittoptimierung - Sebastian Hanisch", layout="wide")

st.title("📏 Zuschnittoptimierung (Cutting Stock)")
st.markdown(
    """
Interaktive Demo zum **Cutting Stock Problem**: Ein Rollenkatalog mit mehreren Längen und Kosten soll
in bestellte Zuschnittlängen zerlegt werden - mit möglichst geringen Gesamtkosten. Verglichen werden
eine naive Greedy-Heuristik (**First-Fit-Decreasing**) und **Column Generation**, die iterativ genau
die wertvollsten Schnittmuster über alle Rollentypen hinweg findet, ohne je alle möglichen Muster
aufzählen zu müssen. Hintergrund im Expander "Wie funktioniert diese Demo?" unten sowie formal
hergeleitet im Expander "📐 Mathematische Formulierung".
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_cols = st.columns(len(PRESETS))
for col, name in zip(preset_cols, PRESETS):
    with col:
        st.button(name, use_container_width=True, on_click=apply_preset, args=(name,))

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.markdown("**Verfügbare Rollentypen**")
    stock_df = st.data_editor(
        st.session_state.stock_df, num_rows="dynamic", use_container_width=True,
        column_config={
            "Länge (m)": st.column_config.NumberColumn(min_value=0.1, step=0.5),
            "Kosten (€)": st.column_config.NumberColumn(min_value=0.01, step=0.5),
        },
    )

    st.markdown("**🎲 Zufällige Bestellung**")
    n_types = st.slider("Anzahl Bestelltypen", *bounds("n_types_slider"), key="n_types_slider")
    seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), step=1, key="seed_input")
    st.button(
        "🎲 Zufällige Bestellung generieren", use_container_width=True, on_click=randomize_orders,
        help="Erzeugt eine neue zufällige Bestelltabelle mit der gewählten Anzahl Bestelltypen "
             "(würfelt bei jedem Klick einen neuen Seed).",
    )

    st.markdown("**Bestellungen**")
    orders_df = st.data_editor(
        st.session_state.orders_df, num_rows="dynamic", use_container_width=True,
        column_config={
            "Länge (m)": st.column_config.NumberColumn(min_value=0.1, step=0.1),
            "Bedarf (Stück)": st.column_config.NumberColumn(min_value=1, step=1),
        },
    )

stock_types = stock_types_from_df(stock_df)
if not stock_types:
    st.warning("Mindestens ein gültiger Rollentyp (Länge > 0) wird benötigt.")
    st.stop()
max_stock_length = max(s.length for s in stock_types)

orders = [
    (str(row["Label"]), float(row["Länge (m)"]), int(row["Bedarf (Stück)"]))
    for _, row in orders_df.dropna().iterrows()
    if float(row["Länge (m)"]) <= max_stock_length
]

if not orders:
    st.warning(f"Mindestens eine gültige Bestellung mit Länge ≤ {max_stock_length:.1f} m (längster Rollentyp) wird benötigt.")
    st.stop()

sync_query_params(orders, stock_types, n_types, seed)

problem = build_problem(orders, stock_types)

with st.spinner("Löse..."):
    ffd_patterns, ffd_stock_idx, ffd_counts = ffd_heuristic(problem)
    cg_result = column_generation(problem)

ffd_summary = summarize(problem, ffd_patterns, ffd_stock_idx, ffd_counts)
cg_summary = summarize(problem, cg_result.patterns, cg_result.stock_idx, cg_result.pattern_counts)

st.markdown("## 🎯 Ergebnis im Vergleich")
m1, m2, m3, m4 = st.columns(4)
m1.metric(
    "FFD-Heuristik", f"{ffd_summary.total_cost:.2f} €",
    delta=f"{ffd_summary.total_rolls} Rollen · {ffd_summary.waste_pct:.1f} % Verschnitt", delta_color="off",
)
m2.metric(
    "Column Generation", f"{cg_summary.total_cost:.2f} €",
    delta=f"{cg_summary.total_rolls} Rollen · {cg_summary.waste_pct:.1f} % Verschnitt", delta_color="off",
    help="Verschnitt = ungenutzte Rollenreste + überzählig geschnittene Stücke (Column Generation deckt Bedarf "
         "mit ≥ statt =, kann also vereinzelt mehr als bestellt schneiden - das zählt hier bewusst als "
         "Verschnitt, sonst wäre der Vergleich mit FFD nicht fair).",
)
saved_cost = ffd_summary.total_cost - cg_summary.total_cost
m3.metric(
    "Gesparte Kosten", f"{saved_cost:.2f} €",
    delta=f"{100 * saved_cost / ffd_summary.total_cost:.1f} %" if ffd_summary.total_cost else None,
)
m4.metric(
    "LP-Schranke (Beweis)", f"{cg_result.lp_relaxation_cost:.2f} €",
    help="Mathematisch bewiesenes Kosten-Minimum, das keine Lösung unterschreiten kann - egal welches Verfahren.",
)

if cg_summary.overproduction_length > 1e-6:
    st.caption(
        f"↪️ Davon {cg_summary.overproduction_length:.2f} m bei Column Generation überzählig geschnitten "
        f"(mehr als bestellt) - eine Nebenwirkung der Rundung von der LP-Lösung auf ganze Rollen."
    )

if abs(saved_cost) < 1e-6:
    st.info(
        "In diesem Szenario erreicht die einfache FFD-Heuristik zufällig bereits dieselben Kosten wie Column "
        "Generation. Der Unterschied: Nur Column Generation liefert mit der LP-Schranke auch den **Beweis**, "
        "dass keine Lösung günstiger sein kann. Probieren Sie ein anderes Szenario oder eigene Bestellungen/"
        "Rollentypen aus, um einen Fall zu sehen, in dem FFD tatsächlich mehr kostet."
    )

pdf_bytes = generate_cutting_report_pdf(
    problem, orders, stock_types, ffd_patterns, ffd_stock_idx, ffd_counts, ffd_summary, cg_result, cg_summary,
)
st.download_button(
    "📄 Vergleichsbericht als PDF herunterladen", data=pdf_bytes,
    file_name="zuschnittoptimierung.pdf", mime="application/pdf",
)

tab_cg, tab_ffd = st.tabs(["Column Generation", "FFD-Heuristik"])
with tab_cg:
    st.plotly_chart(
        pattern_figure(problem, cg_result.patterns, cg_result.stock_idx, cg_result.pattern_counts, "Schnittmuster (Column Generation)"),
        use_container_width=True,
    )
with tab_ffd:
    st.plotly_chart(
        pattern_figure(problem, ffd_patterns, ffd_stock_idx, ffd_counts, "Schnittmuster (FFD)"),
        use_container_width=True,
    )

with st.expander("❓ Wie funktioniert diese Demo?"):
    st.markdown(
        """
**Das Problem:** Aus einem Katalog von Rollen mit mehreren Längen und Kosten sollen die bestellten
Stückzahlen jeder Zuschnittlänge herausgeschnitten werden - mit möglichst geringen Gesamtkosten. Ein
*Schnittmuster* legt fest, wie viele Stücke welcher Länge aus einer einzelnen Rolle eines bestimmten
Rollentyps geschnitten werden.

**Warum nicht einfach alle Muster durchprobieren?** Schon bei wenigen Bestelltypen gibt es
astronomisch viele gültige (Rollentyp, Muster)-Kombinationen. Für reale Bestelllisten ist
Enumeration unmöglich.

**First-Fit-Decreasing (FFD):** Sortiert alle benötigten Einzelstücke absteigend nach Länge und
legt jedes Stück in die erste offene Rolle, in der noch Platz ist - sonst wird eine neue Rolle
begonnen, und zwar vom **billigsten Rollentyp, der für dieses eine Stück gerade noch reicht**.
Schnell, aber eine rein lokale Entscheidung: FFD sieht beim Öffnen einer Rolle nie, welche anderen
Stücke später noch dazukommen könnten.

**Column Generation:** Startet mit einer Handvoll einfacher Muster (je ein Muster pro Bestelltyp,
im jeweils kürzesten passenden Rollentyp) und löst die *LP-Relaxierung* eines Optimierungsmodells,
das die güntigste Mischung aus (Rollentyp, Muster)-Kombinationen sucht. Die Lösung liefert
**Dualwerte** - im Grunde einen "Wert pro Meter" für jeden Bestelltyp. Pro Rollentyp sucht ein
kleines Rucksack-Teilproblem darauf aufbauend das eine neue Muster, das diese Werte am besten
ausnutzt; das über alle Rollentypen wertvollste wird ergänzt und die LP erneut gelöst - so lange,
bis keine (Rollentyp, Muster)-Kombination mehr eine Verbesserung bringt. Weil dabei jede Iteration
alle Rollentypen gleichzeitig bewertet, findet Column Generation Kombinationen (z. B. "dieser lange,
teurere Rollentyp lohnt sich nur, weil er drei verschiedene Bestelltypen exakt kombiniert"), die FFDs
rein lokale "billigste passende Rolle"-Regel systematisch übersieht. Das fertige LP-Ergebnis wird
anschließend auf eine ganzzahlige Lösung gerundet. Da das Modell Bedarf mit ≥ statt = deckt, kann
diese Rundung vereinzelt mehr Stücke eines Typs erzeugen als bestellt - dieser Überschuss zählt in
der Verschnitt-Kennzahl oben bewusst mit, sonst wäre der Vergleich mit FFD (die nie mehr als
bestellt schneidet) nicht fair.
"""
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Master-Problem** (Muster $j$ mit Stückzahlvektor $a_j$, geschnitten aus Rollentyp $k(j)$ zu Kosten
$c_{k(j)}$, Einsatzhäufigkeit $x_j \geq 0$):

$$\min \sum_j c_{k(j)}\, x_j \quad \text{s.t.} \quad \sum_j a_{ij}\, x_j \geq d_i \ \ \forall i, \quad x_j \geq 0$$

Die LP-Relaxierung (reelle statt ganzzahlige $x_j$) liefert die Dualwerte $y_i \geq 0$ für jede
Bestellzeile - ökonomisch: "wie viel eine zusätzliche Einheit Bedarf $i$ die Gesamtlösung
verteuern würde".

**Pricing-Teilproblem** (ein Rucksackproblem pro Rollentyp $k$ mit Länge $L_k$ und Kosten $c_k$:
welches neue Muster lohnt sich?):

$$\max \sum_i y_i\, a_i \quad \text{s.t.} \quad \sum_i \ell_i\, a_i \leq L_k, \quad a_i \in \mathbb{Z}_{\geq 0}$$

mit Stücklänge $\ell_i$. Für jeden Rollentyp $k$ wird dieses Rucksackproblem gelöst; das Muster mit
den kleinsten reduzierten Kosten $c_k - \sum_i y_i a_i$ über alle Rollentypen hinweg verbessert die
Lösung am meisten. Ist dieser Wert $< 0$, wird die zugehörige (Rollentyp, Muster)-Kombination
ergänzt; ist keine solche Kombination mehr zu finden, ist die LP-Relaxierung bewiesen optimal.

**Rundung:** Aus der optimalen fraktionalen Lösung werden die vollen Rollen je (Rollentyp,
Muster)-Kombination (abgerundet) übernommen; der kleine Rest wird mit FFD aufgefüllt - ein
Standardverfahren, das garantiert zulässig bleibt, ohne vollständiges Branch-and-Price zu benötigen.
"""
    )

st.caption(
    f"Column Generation brauchte {cg_result.iterations} Iterationen, um {len(cg_result.patterns)} "
    f"(Rollentyp, Muster)-Kombinationen zu finden (statt aller theoretisch möglichen)."
)
