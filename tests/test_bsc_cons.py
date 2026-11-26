"""Testes das regras de ICPP, IPP e IAP com um cronograma pequeno e conhecido.

Execução (na raiz do repositório):  python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "bsc"))
import bsc_cons  # noqa: E402


def make_activities(rows):
    df = pd.DataFrame(rows, columns=["Projeto", "Atividade", "Recursos", "Percentual completo", "Inicio", "Termino"])
    df["Percentual completo"] = df["Percentual completo"].astype(str)
    df["Inicio"] = pd.to_datetime(df["Inicio"])
    df["Termino"] = pd.to_datetime(df["Termino"])
    df["Percentual"] = df["Percentual completo"].astype(float)
    df["Mes"] = df["Termino"].dt.strftime("%Y-%m")
    return df


ROWS = [
    # Projeto A: em janeiro, 2 de 2 concluídas; em fevereiro, 1 de 2 (atraso).
    ("A", "a1", "Marketing", 100, "2026-01-05", "2026-01-10"),
    ("A", "a2", "P&D", 100, "2026-01-12", "2026-01-20"),
    ("A", "a3", "Marketing", 100, "2026-02-02", "2026-02-10"),
    ("A", "a4", "P&D, Cliente", 40, "2026-02-11", "2026-02-20"),
    ("A", "a6", "Marketing", 100, "2026-02-21", "2026-02-25"),
    ("A", "a5", "Marketing", 0, "2026-03-02", "2026-03-10"),  # ainda não venceu
    # Projeto B: tudo concluído em janeiro e fevereiro.
    ("B", "b1", "Marketing", 100, "2026-01-05", "2026-01-15"),
    ("B", "b2", "Desconhecido (-65535)", 100, "2026-02-02", "2026-02-12"),
]


class BscConsTest(unittest.TestCase):
    def setUp(self):
        self.activities = make_activities(ROWS)
        self.references = bsc_cons.infer_reference_dates(self.activities)
        self.due = bsc_cons.due_activities(self.activities, self.references)

    def test_reference_date_is_last_evidence_of_execution(self):
        self.assertEqual(self.references["A"], pd.Timestamp("2026-02-25"))  # último término concluído
        self.assertEqual(self.references["B"], pd.Timestamp("2026-02-12"))  # último término concluído

    def test_future_activities_are_not_due(self):
        self.assertNotIn("a5", set(self.due["Atividade"]))

    def test_ipp_counts_projects_with_all_planned_activities_done(self):
        monthly = bsc_cons.build_monthly_activities(self.due)
        ipp = bsc_cons.build_ipp(monthly).set_index("Month")
        self.assertEqual(ipp.loc["2026-01", "ProjetosAtivos"], 2)
        self.assertEqual(ipp.loc["2026-01", "IPP"], 100.0)
        self.assertEqual(ipp.loc["2026-02", "ProjetosConformes"], 1)  # B conforme, A não (a4 venceu e está incompleta)
        self.assertEqual(ipp.loc["2026-02", "IPP"], 50.0)

    def test_iap_by_sector_ignores_client_and_unassigned(self):
        iap = bsc_cons.build_iap(self.due)
        self.assertEqual(set(iap["Setor"]), {"Marketing", "P&D"})
        marketing = iap[(iap["Setor"] == "Marketing") & (iap["Month"] == "2026-01")].iloc[0]
        self.assertEqual((marketing["AtividadesPlanejadas"], marketing["IAP"]), (2, 100.0))
        # a4 está atrasada e compartilhada com o Cliente: pesa só para P&D.
        pd_feb = iap[(iap["Setor"] == "P&D") & (iap["Month"] == "2026-02")].iloc[0]
        self.assertEqual((pd_feb["AtividadesPlanejadas"], pd_feb["AtividadesRealizadas"], pd_feb["IAP"]), (1, 0, 0.0))

    def test_icpp_is_ratio_of_cumulative_percentages_until_reference_month(self):
        previsto = pd.DataFrame({"Projeto": ["A"] * 3, "Month": ["2026-01", "2026-02", "2026-03"], "CumulativePercent": [40, 80, 100]})
        realizado = pd.DataFrame({"Projeto": ["A"] * 3, "Month": ["2026-01", "2026-02", "2026-03"], "CumulativePercent": [40, 60, 70]})
        icpp = bsc_cons.build_icpp(previsto, realizado, self.references)
        self.assertEqual(list(icpp["Month"]), ["2026-01", "2026-02"])  # março ainda não foi avaliado
        self.assertEqual(icpp.iloc[0]["ICPP"], 1.0)
        self.assertAlmostEqual(icpp.iloc[1]["ICPP"], 0.75)
        self.assertEqual(icpp.iloc[1]["DeltaAV"], -20)
        self.assertTrue(icpp.iloc[1]["MesParcial"])  # referência em 25/02, antes do fim do mês

    def test_fixed_reference_date_applies_to_every_project(self):
        refs = bsc_cons.infer_reference_dates(self.activities, "2026-03-31")
        due = bsc_cons.due_activities(self.activities, refs)
        self.assertIn("a5", set(due["Atividade"]))


if __name__ == "__main__":
    unittest.main()
