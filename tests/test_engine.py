import unittest
import sys
import os
import json

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import init_db, get_connection
from db.repository import save_property_record, save_new_lead, update_lead_crm, get_crm_leads
from analytics.score_engine import calculate_gdzielokum_score, SCORE_DISCLAIMER
from analytics.ai_search import parse_natural_language_query, explain_ai_matching
from analytics.investor_calculator import calculate_rental_roi, calculate_flip_profit
from scrapers.source_adapter import get_registered_adapters
from reports.client_report import generate_client_catalog_html

class TestGdzieLokumEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_database_and_repository(self):
        test_prop = {
            "id": "test_prop_001",
            "title": "Apartament w centrum Wrocławia",
            "city": "wroclaw",
            "total_price": 600000,
            "area": 60.0,
            "price_per_m2": 10000.0,
            "rooms": 3,
            "is_private": True,
            "has_balcony": True,
            "source": "OLX"
        }
        save_property_record(test_prop)
        
        lid = save_new_lead(test_prop["id"], "Tomasz Kowal", "+48 500 111 222", "tomasz@test.pl")
        self.assertGreater(lid, 0)
        
        update_lead_crm(lid, "Spotkanie umówione", next_contact_date="2026-10-05", note="Klient zdecydowany")
        leads = get_crm_leads()
        found = any(l["id"] == lid for l in leads)
        self.assertTrue(found)

    def test_gdzielokum_score(self):
        market_stats = {"median_m2": 12000.0, "avg_m2": 12100.0}
        
        cheap_offer = {"total_price": 480000, "area": 50.0, "price_per_m2": 9600.0, "rooms": 2, "has_balcony": True}
        res_cheap = calculate_gdzielokum_score(cheap_offer, market_stats)
        self.assertGreaterEqual(res_cheap["score"], 70)
        self.assertIn("GdzieLokum SCORE", res_cheap["disclaimer"])

        expensive_offer = {"total_price": 780000, "area": 50.0, "price_per_m2": 15600.0, "rooms": 2}
        res_expensive = calculate_gdzielokum_score(expensive_offer, market_stats)
        self.assertLess(res_expensive["score"], 60)

    def test_ai_search_parser(self):
        query = "Znajdź mi mieszkanie we Wrocławiu do 650 tys., minimum 55 m², 3 pokoje, balkon, najlepiej poniżej ceny rynkowej."
        params = parse_natural_language_query(query)
        self.assertEqual(params["city"], "wroclaw")
        self.assertEqual(params["max_price"], 650000)
        self.assertEqual(params["min_area"], 55.0)
        self.assertEqual(params["rooms"], 3)
        self.assertTrue(params["has_balcony"])

    def test_investor_calculators(self):
        roi = calculate_rental_roi(purchase_price=500000, monthly_rent=3000, area=50.0)
        self.assertEqual(roi["status"], "calculated")
        self.assertGreater(roi["roi_gross_pct"], 5.0)
        self.assertGreater(roi["monthly_net_cashflow"], 2000)

        roi_missing = calculate_rental_roi(purchase_price=0)
        self.assertEqual(roi_missing["status"], "insufficient_data")
        self.assertIn("Brak wystarczających danych", roi_missing["message"])

        flip = calculate_flip_profit(purchase_price=400000, area=50.0, renovation_standard="Standard", arv_markup_pct=25.0)
        self.assertEqual(flip["status"], "calculated")
        self.assertGreater(flip["net_profit"], 0)

    def test_source_adapters_registry(self):
        adapters = get_registered_adapters()
        self.assertGreaterEqual(len(adapters), 4)
        names = [a.name for a in adapters]
        self.assertIn("Otodom", names)
        self.assertIn("OLX", names)
        self.assertIn("Nieruchomości-online", names)

    def test_client_report_generation(self):
        mock_offers = [{
            "id": "rep_01",
            "title": "Stylowy apartament z tarasem",
            "total_price": 750000,
            "area": 70,
            "rooms": 3,
            "price_per_m2": 10714,
            "score": 88,
            "diff_pct": -8.5,
            "location": "Wrocław, Krzyki"
        }]
        html_out = generate_client_catalog_html(
            agency_name="Top Nieruchomości",
            agent_name="Marek Nowak",
            agent_phone="+48 600 700 800",
            agency_email="biuro@topnieruchomosci.pl",
            client_name="Jan Kowalski",
            selected_offers=mock_offers
        )
        self.assertIn("Top Nieruchomości", html_out)
        self.assertIn("Stylowy apartament z tarasem", html_out)
        self.assertIn("88/100", html_out)
        self.assertNotIn("otodom.pl", html_out)
        self.assertNotIn("olx.pl", html_out)

if __name__ == "__main__":
    unittest.main()
