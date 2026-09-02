"""
Erzeugt einen Vergleichsbericht (FFD vs. Column Generation) als downloadbares
PDF (in-memory) - Zusammenfassung, Rollenkatalog, Bestellliste und die
verwendeten Schnittmuster je Verfahren.
"""

import time

import numpy as np


def _pattern_composition(pattern: np.ndarray, labels: tuple) -> str:
    parts = [f"{int(count)}×{label}" for label, count in zip(labels, pattern) if count > 0]
    return ", ".join(parts)


def generate_cutting_report_pdf(
    problem, orders, stock_types, ffd_patterns, ffd_stock_idx, ffd_counts, ffd_summary, cg_result, cg_summary,
):
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Zuschnittoptimierung - Vergleichsbericht", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')} Uhr", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Zusammenfassung", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0, 6,
        f"FFD-Heuristik: {ffd_summary.total_cost:.2f} EUR ({ffd_summary.total_rolls} Rollen, "
        f"{ffd_summary.waste_pct:.1f} % Verschnitt)",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.cell(
        0, 6,
        f"Column Generation: {cg_summary.total_cost:.2f} EUR ({cg_summary.total_rolls} Rollen, "
        f"{cg_summary.waste_pct:.1f} % Verschnitt)",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    if cg_summary.overproduction_length > 1e-6:
        pdf.cell(
            0, 6,
            f"Davon {cg_summary.overproduction_length:.2f} m überzählig geschnitten (mehr als bestellt, "
            f"Nebenwirkung der Rundung von der LP-Lösung auf ganze Rollen)",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
    pdf.cell(
        0, 6,
        f"LP-Schranke (Beweis): {cg_result.lp_relaxation_cost:.2f} EUR, "
        f"gefunden in {cg_result.iterations} Iterationen mit {len(cg_result.patterns)} Mustern",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Rollenkatalog", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    headers = ["Rollentyp", "Länge (m)", "Kosten (EUR)"]
    widths = [60, 60, 60]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(235, 235, 235)
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, h, border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    for stock in stock_types:
        row = [stock.label, f"{stock.length:.2f}", f"{stock.cost:.2f}"]
        for val, w in zip(row, widths):
            pdf.cell(w, 6, val, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(6)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Bestellungen", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    headers = ["Label", "Länge (m)", "Bedarf (Stück)"]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(235, 235, 235)
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, h, border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    for label, length, demand in orders:
        row = [label, f"{length:.2f}", str(demand)]
        for val, w in zip(row, widths):
            pdf.cell(w, 6, val, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(6)
    pdf.ln(4)

    for title, patterns, stock_idx, counts in [
        ("Schnittmuster (Column Generation)", cg_result.patterns, cg_result.stock_idx, cg_result.pattern_counts),
        ("Schnittmuster (FFD)", ffd_patterns, ffd_stock_idx, ffd_counts),
    ]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        headers = ["Muster", "Rollentyp", "Zusammensetzung", "Anzahl"]
        pattern_widths = [15, 40, 90, 35]
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(235, 235, 235)
        for h, w in zip(headers, pattern_widths):
            pdf.cell(w, 7, h, border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(7)

        pdf.set_font("Helvetica", "", 9)
        order = sorted((j for j in range(len(counts)) if counts[j] > 0), key=lambda j: -counts[j])
        for rank, j in enumerate(order):
            row = [
                str(rank + 1),
                stock_types[stock_idx[j]].label,
                _pattern_composition(patterns[j], problem.labels),
                str(int(counts[j])),
            ]
            for val, w in zip(row, pattern_widths):
                pdf.cell(w, 6, val, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.ln(6)
        pdf.ln(4)

    return bytes(pdf.output())
