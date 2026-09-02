# 📏 Zuschnittoptimierung (Cutting Stock Problem)

Interaktive Demo zum Cutting-Stock-Problem mit mehreren Rollentypen: Ein Lieferant führt mehrere Standard-Rollenlängen (Stahl, Kabel, Papier) zu unterschiedlichen Kosten, aus denen bestellte Zuschnittlängen zerlegt werden sollen — mit möglichst geringen Gesamtkosten.

**[→ Demo live ausprobieren](https://sebastianhanisch-cutting-stock-demo.streamlit.app/)**

## Worum geht's?

Die einzige klassische OR-Technik im Portfolio, die bisher fehlte: **Column Generation**. Statt alle möglichen (Rollentyp, Schnittmuster)-Kombinationen aufzuzählen (schon bei wenigen Bestelltypen praktisch unzählbar viele), startet das Verfahren mit ein paar trivialen Mustern, löst die LP-Relaxierung eines "günstigste Mustermischung"-Modells und nutzt deren Dualwerte, um über je ein kleines Rucksack-Teilproblem pro Rollentyp gezielt genau die eine wertvollste neue Kombination zu finden — bis keine mehr eine Verbesserung bringt.

Verglichen wird das mit **First-Fit-Decreasing (FFD)**, einer schnellen, naiven Greedy-Heuristik, die beim Öffnen einer neuen Rolle immer den billigsten Rollentyp wählt, der für das aktuelle Stück gerade noch reicht — eine rein lokale Entscheidung ohne Blick auf die restliche Bestellung. Kernthema der Demo: Weil Column Generation bei jeder Iteration alle Rollentypen gleichzeitig bewertet, findet es Kombinationen (z. B. "dieser lange, teurere Rollentyp lohnt sich nur, weil er mehrere Bestelltypen exakt kombiniert"), die FFDs "billigste passende Rolle"-Regel systematisch übersieht — im Preset "Worst Case für FFD" ist das ~22 % teurer, und die LP-Schranke beweist, dass Column Generation dort exakt optimal liegt.

## Methodik

- Column Generation: LP-Master-Problem via SciPy `linprog` (HiGHS), Pricing-Teilproblem als unbeschränktes Rucksackproblem pro Rollentyp via exakter dynamischer Programmierung; das über alle Rollentypen wertvollste neue Muster wird je Iteration ergänzt
- Rundung der fraktionalen LP-Lösung auf eine ganzzahlige Lösung: volle Rollen je (Rollentyp, Muster)-Kombination abgerundet übernehmen, Rest per FFD auffüllen (Standardverfahren, bleibt beweisbar zulässig, ohne vollständiges Branch-and-Price)
- First-Fit-Decreasing als unabhängige Vergleichsheuristik, erweitert um eine "billigster passender Rollentyp"-Regel beim Öffnen neuer Rollen
- Test gegen ein von Hand nachrechenbares Beispiel (Stocklänge 10, Stücke 6 und 4 mit je 5 Bedarf): die optimale Lösung nutzt ein kombiniertes Muster [1×6, 1×4] mit exakt 0 Verschnitt — dieser Test verifiziert, dass das Pricing-Teilproblem tatsächlich kombinierte Muster findet und nicht nur triviale Ein-Item-Muster (siehe `tests/test_solver.py`)
- Verschnitt zählt physische Rollenreste **und** durch die Rundung entstandene Überproduktion (Bedarf wird mit ≥ statt = gedeckt), damit die Kennzahl zwischen FFD und Column Generation fair vergleichbar bleibt
- Mathematische Herleitung (Master-Problem, Dualwerte, Pricing-Teilproblem je Rollentyp) im Expander „Mathematische Formulierung“

## Lokal ausführen

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

Tests: `pytest tests/ -v`

---

Teil des [Operations-Research-Demo-Portfolios](https://sebastianhanisch.net/demos.html) von [Sebastian Hanisch](https://sebastianhanisch.net) — Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html).
