"""
Erzeugt einen Vergleichsbericht (FFD vs. Column Generation) als downloadbares
PDF (in-memory) - Zusammenfassung, Bestellliste und die verwendeten
Schnittmuster je Verfahren.
"""

import time

import numpy as np


def _pattern_composition(pattern: np.ndarray, labels: tuple) -> str:
    parts = [f"{int(count)}×{label}" for label, count in zip(labels, pattern) if count > 0]
    return ", ".join(parts)


def generate_cutting_report_pdf(problem, orders, ffd_patterns, ffd_counts, ffd_summary, cg_result, cg_summary):
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
    pdf.cell(0, 6, f"Rollenlänge: {problem.roll_length:.2f} m", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(
        0, 6,
        f"FFD-Heuristik: {ffd_summary.total_rolls} Rollen ({ffd_summary.waste_pct:.1f} % Verschnitt)",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.cell(
        0, 6,
        f"Column Generation: {cg_summary.total_rolls} Rollen ({cg_summary.waste_pct:.1f} % Verschnitt)",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.cell(
        0, 6,
        f"LP-Schranke (Beweis): {cg_result.lp_relaxation_rolls:.2f} Rollen, "
        f"gefunden in {cg_result.iterations} Iterationen mit {len(cg_result.patterns)} Mustern",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Bestellungen", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    headers = ["Label", "Länge (m)", "Bedarf (Stück)"]
    widths = [60, 60, 60]
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

    for title, patterns, counts in [
        ("Schnittmuster (Column Generation)", cg_result.patterns, cg_result.pattern_counts),
        ("Schnittmuster (FFD)", ffd_patterns, ffd_counts),
    ]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        headers = ["Muster", "Zusammensetzung", "Anzahl Rollen"]
        widths = [20, 130, 30]
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(235, 235, 235)
        for h, w in zip(headers, widths):
            pdf.cell(w, 7, h, border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(7)

        pdf.set_font("Helvetica", "", 9)
        order = sorted((j for j in range(len(counts)) if counts[j] > 0), key=lambda j: -counts[j])
        for rank, j in enumerate(order):
            row = [str(rank + 1), _pattern_composition(patterns[j], problem.labels), str(int(counts[j]))]
            for val, w in zip(row, widths):
                pdf.cell(w, 6, val, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.ln(6)
        pdf.ln(4)

    return bytes(pdf.output())
