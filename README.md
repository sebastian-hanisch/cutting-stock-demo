# 📏 Zuschnittoptimierung (Cutting Stock Problem)

Interaktive Demo zum klassischen Cutting-Stock-Problem: Rollen/Stangen fester Länge (Stahl, Kabel, Papier) werden in bestellte Zuschnittlängen zerlegt — mit möglichst wenig Rollen und möglichst wenig Verschnitt.

## Worum geht's?

Die einzige klassische OR-Technik im Portfolio, die bisher fehlte: **Column Generation**. Statt alle möglichen Schnittmuster aufzuzählen (schon bei wenigen Bestelltypen praktisch unzählbar viele), startet das Verfahren mit ein paar trivialen Mustern, löst die LP-Relaxierung eines "günstigste Mustermischung"-Modells und nutzt deren Dualwerte, um über ein kleines Rucksack-Teilproblem gezielt genau das eine wertvollste neue Muster zu finden — bis kein Muster mehr eine Verbesserung bringt.

Verglichen wird das mit **First-Fit-Decreasing (FFD)**, einer schnellen, naiven Greedy-Heuristik. Kernthema der Demo: FFD ist für Cutting-Stock-Probleme überraschend stark und liegt in vielen Szenarien gleichauf mit Column Generation — der eigentliche Mehrwert von Column Generation ist nicht immer "weniger Rollen", sondern die **LP-Schranke als mathematischer Beweis**, wie nah jede Lösung höchstens am Optimum liegen kann. Das kann eine reine Heuristik grundsätzlich nicht liefern.

## Methodik

- Column Generation: LP-Master-Problem via SciPy `linprog` (HiGHS), Pricing-Teilproblem als unbeschränktes Rucksackproblem via exakter dynamischer Programmierung
- Rundung der fraktionalen LP-Lösung auf eine ganzzahlige Lösung: volle Rollen je Muster abgerundet übernehmen, Rest per FFD auffüllen (Standardverfahren, bleibt beweisbar zulässig, ohne vollständiges Branch-and-Price)
- First-Fit-Decreasing als unabhängige Vergleichsheuristik
- Test gegen ein von Hand nachrechenbares Beispiel (Rollenlänge 10, Stücke 6 und 4 mit je 5 Bedarf): die optimale Lösung nutzt ein kombiniertes Muster [1×6, 1×4] mit exakt 0 Verschnitt — dieser Test verifiziert, dass das Pricing-Teilproblem tatsächlich kombinierte Muster findet und nicht nur triviale Ein-Item-Muster (siehe `tests/test_solver.py`)
- Mathematische Herleitung (Master-Problem, Dualwerte, Pricing-Teilproblem) im Expander „Mathematische Formulierung“

## Lokal ausführen

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

Tests: `pytest tests/ -v`

---

Teil des [Operations-Research-Demo-Portfolios](https://sebastianhanisch.net/demos.html) von [Sebastian Hanisch](https://sebastianhanisch.net) — Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html).
