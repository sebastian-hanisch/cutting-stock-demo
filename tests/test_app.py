"""End-to-end Smoke-Test via Streamlits offizielles AppTest-Framework: laedt app.py mit
den Standardeinstellungen und prueft, dass kein Python-Fehler auftritt. Ergaenzt die
funktionalen Unit-Tests der uebrigen Module - ein Fehler wie
`streamlit.errors.StreamlitDuplicateElementId` (zwei st.plotly_chart-Aufrufe ohne
eindeutiges key= rendern zufaellig identischen Inhalt und kollidieren) liegt in app.py's
Widget-Verdrahtung selbst und kann nur durch einen echten End-to-End-Lauf gefunden werden,
nicht durch Unit-Tests der Algorithmus-/Visualisierungs-Module (siehe hdbscan-demo, wo
genau dieser Fehlertyp bei einem echten Nutzer auftrat, 2026-09-05)."""

import os

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def test_app_loads_without_exception():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=120)
    assert not at.exception, [str(e) for e in at.exception]


def test_equal_cost_info_does_not_claim_cg_proves_optimality():
    """Gleiche Kosten von FFD und Column Generation (A 6,9 m x 13, B 13,1 m x 12; Standard-Rollentypen: beide 176,50 €,
    LP-Schranke 173,00 €): der Infotext darf nicht behaupten, nur Column Generation beweise, dass nichts günstiger ist,
    sondern muss die LP-Schranke als untere Grenze nennen und sagen, dass die Lösung darüber liegt."""
    at = AppTest.from_file(APP_PATH)
    at.query_params["orders"] = "A:6.9:13,B:13.1:12"
    at.run(timeout=120)
    assert not at.exception, [str(e) for e in at.exception]
    text = " ".join(i.value for i in at.info)
    assert "dieselben Kosten" in text and "Bewiesen ist nur die LP-Schranke (173.00" in text
    assert "keine Lösung günstiger sein kann" not in text and "liegt darüber" in text
