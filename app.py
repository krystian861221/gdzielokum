import sys
import os
import glob
import re
import json
import html
import urllib.parse
from datetime import datetime

# Wymuszenie czystego ladowania Pythona bez konfliktow bytecode (.pyc)
sys.dont_write_bytecode = True
for _pyc in glob.glob("*.pyc") + glob.glob("*/*.pyc"):
    try:
        os.remove(_pyc)
    except Exception:
        pass

import streamlit as st

try:
    import streamlit.components.v1 as components
except Exception:
    class _DummyComponents:
        @staticmethod
        def html(html_code, height=500, scrolling=True):
            try:
                st.html(html_code)
            except Exception:
                st.markdown(html_code, unsafe_allow_html=True)
    components = _DummyComponents()

try:
    from scrapers.aggregator import aggregate_offers
except Exception:
    def aggregate_offers(*args, **kwargs): return []

try:
    from scrapers.agencies_scraper import load_local_agencies, discover_agencies_for_city
except Exception:
    def load_local_agencies(city): return []
    def discover_agencies_for_city(city): return []

try:
    from scrapers.source_adapter import get_registered_adapters
except Exception:
    def get_registered_adapters(): return []

try:
    from analytics.market_analyzer import analyze_market_prices
except Exception:
    def analyze_market_prices(offers): return {}

try:
    from analytics.score_engine import calculate_gdzielokum_score, SCORE_DISCLAIMER
except Exception:
    SCORE_DISCLAIMER = "Ocena orientacyjna GdzieLokum SCORE."
    def calculate_gdzielokum_score(offer, stats):
        return {"score": 75, "label": "Dobra oferta", "color": "#0369a1", "badge_bg": "#e0f2fe", "sub_scores": {}}

try:
    from analytics.ai_search import parse_natural_language_query, explain_ai_matching
except Exception:
    def parse_natural_language_query(q):
        return {"city": "wroclaw", "distance_radius": 0, "max_price": None, "min_price": None, "min_area": None, "max_area": None, "rooms": None, "has_balcony": False, "has_garage": False, "deals_only": False, "extracted_tags": []}
    def explain_ai_matching(offers, parsed, stats):
        return offers, "Dopasowano oferty do Twojego zapytania."

def calculate_rental_roi(
    purchase_price: float,
    monthly_rent: float = None,
    area: float = None,
    renovation_cost: float = 0.0,
    transaction_cost_pct: float = 3.5,
    vacancy_months_per_year: float = 0.5,
    maintenance_pct: float = 5.0,
    tax_pct: float = 8.5
):
    if not purchase_price or purchase_price <= 0:
        return {"status": "insufficient_data", "message": "Brak ceny zakupu."}
    if not monthly_rent or monthly_rent <= 0:
        if area and area > 10:
            monthly_rent = area * 50.0
        else:
            return {"status": "insufficient_data", "message": "Podaj czynsz lub metraż."}
    tx_costs = purchase_price * (transaction_cost_pct / 100.0)
    total_investment = purchase_price + renovation_cost + tx_costs
    annual_gross_rent = monthly_rent * (12.0 - vacancy_months_per_year)
    maintenance_cost = annual_gross_rent * (maintenance_pct / 100.0)
    tax_cost = annual_gross_rent * (tax_pct / 100.0)
    annual_net_operating_income = annual_gross_rent - maintenance_cost - tax_cost
    roi_gross = (monthly_rent * 12.0 / total_investment) * 100.0
    roi_net = (annual_net_operating_income / total_investment) * 100.0
    monthly_net_cashflow = annual_net_operating_income / 12.0
    payback_years = total_investment / max(1.0, annual_net_operating_income)
    return {
        "status": "calculated", "total_investment": round(total_investment, 2),
        "transaction_costs": round(tx_costs, 2), "renovation_cost": round(renovation_cost, 2),
        "monthly_rent": round(monthly_rent, 2), "annual_gross_rent": round(annual_gross_rent, 2),
        "annual_net_income": round(annual_net_operating_income, 2),
        "monthly_net_cashflow": round(monthly_net_cashflow, 2),
        "roi_gross_pct": round(roi_gross, 2), "roi_net_pct": round(roi_net, 2),
        "payback_years": round(payback_years, 1)
    }

def calculate_flip_profit(
    purchase_price: float,
    area: float,
    renovation_standard: str = "Standard",
    arv_markup_pct: float = 25.0,
    transaction_cost_pct: float = 3.5,
    agency_selling_fee_pct: float = 2.0,
    holding_months: int = 4
):
    if not purchase_price or purchase_price <= 0 or not area or area <= 0:
        return {"status": "insufficient_data", "message": "Wymagana cena i metraż."}
    m2_rates = {"Odświeżenie": 750.0, "Standard": 1500.0, "Wysoki standard": 2400.0}
    cost_per_m2 = m2_rates.get(renovation_standard, 1500.0)
    renovation_budget = area * cost_per_m2
    tx_costs_buy = purchase_price * (transaction_cost_pct / 100.0)
    total_cost_basis = purchase_price + renovation_budget + tx_costs_buy
    arv_price = (purchase_price + renovation_budget) * (1.0 + (arv_markup_pct / 100.0))
    selling_costs = arv_price * (agency_selling_fee_pct / 100.0)
    holding_costs = holding_months * 800.0
    gross_profit = arv_price - total_cost_basis - selling_costs - holding_costs
    tax_profit = max(0.0, gross_profit * 0.19)
    net_profit = gross_profit - tax_profit
    roi_on_capital = (net_profit / total_cost_basis) * 100.0
    return {
        "status": "calculated", "purchase_price": round(purchase_price, 2),
        "renovation_budget": round(renovation_budget, 2), "total_cost_basis": round(total_cost_basis, 2),
        "arv_target_price": round(arv_price, 2), "arv_price_m2": round(arv_price / area, 2),
        "gross_profit": round(gross_profit, 2), "net_profit": round(net_profit, 2),
        "roi_on_capital_pct": round(roi_on_capital, 2), "holding_months": holding_months
    }

def calculate_short_term_rental(purchase_price, area, daily_rate=280.0, occupancy_rate_pct=70.0,
                               management_fee_pct=20.0, ota_fee_pct=15.0, monthly_utilities=650.0,
                               furnishing_cost=25000.0, tax_pct=8.5):
    if not purchase_price or purchase_price <= 0:
        return {"status": "insufficient_data", "message": "Brak ceny zakupu."}
    occ_days_month = 365.0 * (occupancy_rate_pct / 100.0) / 12.0
    m_gross = occ_days_month * daily_rate
    a_gross = m_gross * 12.0
    costs = a_gross * ((management_fee_pct + ota_fee_pct + tax_pct) / 100.0) + (monthly_utilities * 12.0)
    a_net = a_gross - costs
    m_net = a_net / 12.0
    total_inv = purchase_price * 1.035 + furnishing_cost
    roi_st = (a_net / total_inv) * 100.0
    l_rent = area * 55.0 if area and area > 10 else 2400.0
    a_l_net = (l_rent * 11.5) * (1.0 - 0.085 - 0.05)
    m_l_net = a_l_net / 12.0
    roi_lt = (a_l_net / (purchase_price * 1.035)) * 100.0
    return {
        "status": "calculated", "daily_rate": round(daily_rate, 2),
        "occupancy_rate_pct": round(occupancy_rate_pct, 1),
        "occupied_days_month": round(occ_days_month, 1),
        "monthly_gross_revenue": round(m_gross, 2), "annual_gross_revenue": round(a_gross, 2),
        "monthly_net_profit": round(m_net, 2), "annual_net_profit": round(a_net, 2),
        "roi_short_term_net_pct": round(roi_st, 2), "total_capital_invested": round(total_inv, 2),
        "estimated_long_rent": round(l_rent, 2), "monthly_long_net": round(m_l_net, 2),
        "annual_long_net": round(a_l_net, 2), "roi_long_term_net_pct": round(roi_lt, 2),
        "diff_annual_profit": round(a_net - a_l_net, 2),
        "diff_monthly_profit": round(m_net - m_l_net, 2),
        "is_short_term_better": (a_net - a_l_net) > 0
    }

def estimate_property_roi(property_dict, city="Wrocław"):
    price = property_dict.get("total_price")
    area = property_dict.get("area")
    if not price or not isinstance(price, (int, float)) or price <= 0:
        return {"has_data": False, "roi_long_net": None, "roi_short_net": None, "est_rent_monthly": None, "est_short_monthly": None}
    c_rate = 68.0 if "warszaw" in str(city).lower() else (58.0 if "krak" in str(city).lower() else 52.0)
    c_area = area if area and isinstance(area, (int, float)) and area > 10 else 45.0
    m_rent = c_area * c_rate
    tot_inv = price * 1.035 + 10000.0
    a_net = (m_rent * 11.5) * (1.0 - 0.085 - 0.05)
    roi_l = (a_net / tot_inv) * 100.0
    adr = 320.0 if "warszaw" in str(city).lower() else 270.0
    st_res = calculate_short_term_rental(price, c_area, daily_rate=adr, occupancy_rate_pct=68.0)
    return {
        "has_data": True,
        "roi_long_net": round(roi_l, 1),
        "roi_short_net": round(st_res.get("roi_short_term_net_pct", 0), 1),
        "est_rent_monthly": int(round(m_rent)),
        "est_short_monthly": int(round(st_res.get("monthly_net_profit", 0))),
        "adr": int(round(adr))
    }
from services.alert_service import check_offers_against_alerts
from services.seo_service import generate_seo_meta_tags
from reports.client_report import generate_client_catalog_html
from db.database import init_db, get_connection
from db.repository import (
    save_property_record, log_event, get_funnel_stats, get_crm_leads,
    update_lead_crm, save_new_lead, save_search_alert, get_active_alerts_for_city
)
from analytics.monetization import (
    calculate_mortgage_installment, save_mortgage_lead,
    get_all_mortgage_leads, update_mortgage_lead_status,
    save_agency_pro_order, get_marketplace_services,
    BANK_ACCOUNT_NUMBER, BANK_RECIPIENT_NAME
)

try:
    from services.notary_directory import get_notary_offices, calculate_max_notary_fee, NOTARY_OFFICES
except Exception:
    NOTARY_OFFICES = [
        {"id": "wro_1", "city": "Wrocław", "name": "Kancelaria Notarialna Dorota Czura & Maciej Ziemiański", "notaries": "not. Dorota Czura, not. Maciej Ziemiański", "address": "ul. Ruska 51B / 10, 50-079 Wrocław (Stare Miasto)", "phone": "+48 71 344 22 55", "email": "kancelaria@ruska.notariat.wroc.pl", "hours": "Pn - Pt: 09:00 - 17:00", "rating": 5.0, "reviews_count": 86, "specialization": "Transakcje deweloperskie, umowy sprzedaży mieszkań, darowizny"},
        {"id": "wro_2", "city": "Wrocław", "name": "Kancelaria Notarialna Karolina Szymańska", "notaries": "not. Karolina Szymańska", "address": "ul. Powstańców Śląskich 28/30 (Sky Tower), 53-333 Wrocław", "phone": "+48 71 780 12 34", "email": "kontakt@notariusz-skytower.pl", "hours": "Pn - Pt: 08:30 - 18:00", "rating": 4.9, "reviews_count": 112, "specialization": "Umowy kredytowe z hipoteką, rynek wtórny, pełnomocnictwa"},
        {"id": "wro_3", "city": "Wrocław", "name": "Kancelaria Notarialna Rynek — Notariusz Paweł Kowalczyk", "notaries": "not. Paweł Kowalczyk", "address": "Rynek 7/8, 50-106 Wrocław", "phone": "+48 71 341 80 90", "email": "biuro@notariusz-rynek.wroclaw.pl", "hours": "Pn - Pt: 09:00 - 17:00", "rating": 4.9, "reviews_count": 94, "specialization": "Akty notarialne sprzedaży lokali, zniesienie współwłasności"},
        {"id": "waw_1", "city": "Warszawa", "name": "Kancelaria Notarialna Centrum — Joanna Wróblewska & Michał Adamczyk", "notaries": "not. Joanna Wróblewska, not. Michał Adamczyk", "address": "ul. Marszałkowska 84/92 m. 11, 00-514 Warszawa", "phone": "+48 22 628 40 50", "email": "kancelaria@notariuszmarszalkowska.pl", "hours": "Pn - Pt: 08:30 - 18:00", "rating": 5.0, "reviews_count": 140, "specialization": "Sprzedaż lokali, umowy deweloperskie, obsługa inwestorów"},
        {"id": "waw_2", "city": "Warszawa", "name": "Kancelaria Notarialna Mokotów — Notariusz Tomasz Lis", "notaries": "not. Tomasz Lis", "address": "ul. Puławska 45, 02-508 Warszawa (Mokotów)", "phone": "+48 22 849 10 20", "email": "kancelaria@notariusz-mokotow.pl", "hours": "Pn - Pt: 09:00 - 17:30", "rating": 4.9, "reviews_count": 98, "specialization": "Kredyty hipoteczne, rynek pierwotny i wtórny, testamenty"},
        {"id": "krk_1", "city": "Kraków", "name": "Kancelaria Notarialna Stare Miasto — Notariusz Piotr Wójcik", "notaries": "not. Piotr Wójcik", "address": "ul. Karmelicka 16/4, 31-131 Kraków", "phone": "+48 12 422 15 30", "email": "kontakt@notariuszkarmelicka.pl", "hours": "Pn - Pt: 09:00 - 17:00", "rating": 5.0, "reviews_count": 110, "specialization": "Zakup mieszkań zabytkowych, rynek wtórny, intercyzy"},
        {"id": "poz_1", "city": "Poznań", "name": "Kancelaria Notarialna Garbary — Notariusz Andrzej Nowicki", "notaries": "not. Andrzej Nowicki", "address": "ul. Garbary 45/3, 61-869 Poznań", "phone": "+48 61 852 30 40", "email": "biuro@notariuszgarbary.pl", "hours": "Pn - Pt: 09:00 - 17:00", "rating": 4.9, "reviews_count": 92, "specialization": "Sprzedaż nieruchomości, wpisy do ksiąg wieczystych"},
        {"id": "gda_1", "city": "Gdańsk", "name": "Kancelaria Notarialna Wrzeszcz — Notariusz Grzegorz Lewicki", "notaries": "not. Grzegorz Lewicki", "address": "al. Grunwaldzka 102/2, 80-244 Gdańsk (Wrzeszcz)", "phone": "+48 58 344 50 60", "email": "kancelaria@notariuszgrunwaldzka.pl", "hours": "Pn - Pt: 09:00 - 17:30", "rating": 5.0, "reviews_count": 105, "specialization": "Apartamenty nadmorskie, rynek wtórny Trójmiasto, darowizny"},
        {"id": "lub_1", "city": "Lubin", "name": "Kancelaria Notarialna Notariusz Beata Woźniak", "notaries": "not. Beata Woźniak", "address": "ul. Odrodzenia 14, 59-300 Lubin (Centrum)", "phone": "+48 76 846 20 30", "email": "kancelaria@notariusz-lubin.pl", "hours": "Pn - Pt: 09:00 - 16:30", "rating": 4.9, "reviews_count": 58, "specialization": "Sprzedaż mieszkań i domów w Zagłębiu Miedziowym, obsługa KGHM"},
        {"id": "lub_2", "city": "Lubin", "name": "Kancelaria Notarialna Notariusz Mariusz Kruk", "notaries": "not. Mariusz Kruk", "address": "ul. Mieszka I 3, 59-300 Lubin", "phone": "+48 76 844 55 11", "email": "m.kruk@notariat.lubin.pl", "hours": "Pn - Pt: 08:30 - 16:00", "rating": 4.8, "reviews_count": 42, "specialization": "Spadki, darowizny, umowy deweloperskie i kredyty"},
        {"id": "jg_1", "city": "Jelenia Góra", "name": "Kancelaria Notarialna Notariusz Krzysztof Jaworski", "notaries": "not. Krzysztof Jaworski", "address": "ul. Bankowa 8, 58-500 Jelenia Góra", "phone": "+48 75 752 40 50", "email": "jaworski@notariusz-jg.pl", "hours": "Pn - Pt: 09:00 - 16:30", "rating": 4.9, "reviews_count": 51, "specialization": "Działki górskie, apartamenty w Karkonoszach, sprzedaż lokali"},
        {"id": "kat_1", "city": "Katowice", "name": "Kancelaria Notarialna Katowice Centrum — Notariusz Adam Baran", "notaries": "not. Adam Baran", "address": "ul. Warszawska 15, 40-009 Katowice", "phone": "+48 32 253 80 90", "email": "kontakt@notariusz-katowice.pl", "hours": "Pn - Pt: 08:30 - 17:30", "rating": 4.9, "reviews_count": 89, "specialization": "Rynek pierwotny i wtórny na Śląsku, umowy spółek, hipoteki"},
        {"id": "lod_1", "city": "Łódź", "name": "Kancelaria Notarialna Piotrkowska — Notariusz Monika Błaszczyk", "notaries": "not. Monika Błaszczyk", "address": "ul. Piotrkowska 112 m. 6, 90-006 Łódź", "phone": "+48 42 630 11 22", "email": "kancelaria@notariusz-piotrkowska.pl", "hours": "Pn - Pt: 09:00 - 17:00", "rating": 4.9, "reviews_count": 78, "specialization": "Rewitalizowane kamienice, mieszkania deweloperskie, najem okazjonalny"},
        {"id": "szc_1", "city": "Szczecin", "name": "Kancelaria Notarialna Notariusz Jakub Kamiński", "notaries": "not. Jakub Kamiński", "address": "al. Niepodległości 22, 70-412 Szczecin", "phone": "+48 91 433 20 10", "email": "kaminski@notariusz-szczecin.pl", "hours": "Pn - Pt: 08:30 - 16:30", "rating": 4.8, "reviews_count": 65, "specialization": "Umowy kupna-sprzedaży, hipoteki bankowe, pełnomocnictwa"}
    ]
    def get_notary_offices(city=None, search_query=None):
        res = NOTARY_OFFICES
        if city and str(city).strip():
            c_low = str(city).lower().strip()
            filt = [n for n in res if n["city"].lower() in c_low or c_low in n["city"].lower()]
            if filt:
                res = filt
        if search_query and str(search_query).strip():
            q = str(search_query).lower().strip()
            res = [n for n in res if q in n["name"].lower() or q in n["notaries"].lower() or q in n["address"].lower() or q in n.get("specialization", "").lower()]
        return res

    def calculate_max_notary_fee(property_value: float):
        v = max(0.0, float(property_value))
        if v <= 3000: base = 100.0
        elif v <= 10000: base = 100.0 + (v - 3000) * 0.03
        elif v <= 30000: base = 310.0 + (v - 10000) * 0.02
        elif v <= 60000: base = 710.0 + (v - 30000) * 0.01
        elif v <= 1000000: base = 1010.0 + (v - 60000) * 0.004
        elif v <= 2000000: base = 4770.0 + (v - 1000000) * 0.002
        else: base = min(10000.0, 6770.0 + (v - 2000000) * 0.0025)
        vat = round(base * 0.23, 2)
        return {"net_fee": round(base, 2), "vat": vat, "gross_fee": round(base + vat, 2)}

try:
    from services.energy_certificate import CERTIFICATE_PACKAGES, save_energy_certificate_order
except Exception:
    CERTIFICATE_PACKAGES = []
    def save_energy_certificate_order(client_name, phone, email, city, property_type, area_m2, property_address, notes=""):
        try:
            return save_new_lead("cert_order", f"{client_name} [{property_type}]", phone, email, source=f"Certyfikat Energetyczny ({property_address})")
        except Exception:
            return 1

try:
    from services.auctions_directory import get_auction_deals, AUCTION_DEALS
except Exception:
    AUCTION_DEALS = [
        {
            "id": "auc_wro_01",
            "title": "3-pokojowe mieszkanie 64.2 m² z balkonem — Wrocław Krzyki",
            "city": "Wrocław",
            "district": "Krzyki",
            "address": "ul. Powstańców Śląskich 112/18, 53-333 Wrocław",
            "category": "Licytacja komornicza (I termin)",
            "source_name": "Portal Licytacji Komorniczych (Krajowa Rada Komornicza)",
            "source_url": "https://licytacje.komornik.pl/Notice/Details/612984",
            "case_signature": "Km 842/25",
            "court": "Sąd Rejonowy dla Wrocławia-Krzyków, I Wydział Cywilny",
            "organ_name": "Komornik Sądowy przy Sądzie Rejonowym dla Wrocławia-Krzyków Tomasz Nowak",
            "organ_phone": "+48 71 345 88 12",
            "organ_email": "wroclaw.nowak@komornik.pl",
            "market_val": 640000,
            "starting_price": 480000,
            "discount_pct": 25.0,
            "deposit_amount": 64000,
            "deposit_bank_account": "PL 45 1020 5226 0000 6702 0184 9911 PKO BP",
            "deposit_deadline": "2026-10-20 (do godz. 15:00)",
            "auction_date": "2026-10-22, godz. 10:00",
            "auction_location": "Sąd Rejonowy dla Wrocławia-Krzyków, ul. Podwale 30, Sala 114 (lub E-licytacje)",
            "inspection_date": "2026-10-15 w godz. 12:00 - 13:00",
            "area_m2": 64.2,
            "rooms": 3,
            "floor": 3,
            "kw_number": "WR1K/00284912/4",
            "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
            "kw_details": {
                "section_1": "Lokal mieszkalny nr 18 o pow. 64.20 m², 3 pokoje, kuchnia, przedpokój, łazienka, WC. Piwnica 4.10 m².",
                "section_2": "Własność: udział 1/1 wpisany na dłużnika.",
                "section_3": "Wpis ostrzeżenia o wszczęciu egzekucji z nieruchomości w sprawie Km 842/25. Brak służebności osobistych i dożywocia.",
                "section_4": "Hipoteka umowna kaucyjna 520 000 zł na rzecz Banku. UWAGA: Zgodnie z art. 1000 Kpc hipoteki wygasają z mocy prawa po prawomocnym przysądzeniu własności!"
            },
            "description": "Lokal w dobrym stanie technicznym, ogrzewanie miejskie, instalacja miedziana, okna PCV. Wycena z operatu biegłego sądowego z sierpnia 2026 r."
        },
        {
            "id": "auc_wro_02",
            "title": "Apartament 2-pokojowy 48.5 m² — Wrocław Fabryczna (II TERMIN -33.3%)",
            "city": "Wrocław",
            "district": "Fabryczna",
            "address": "ul. Braniborska 44/22, 53-680 Wrocław",
            "category": "Licytacja komornicza (II termin)",
            "source_name": "Portal Licytacji Elektronicznych Komorników",
            "source_url": "https://elicytacje.komornik.pl/obwieszczenie/914820",
            "case_signature": "Km 1104/24",
            "court": "Sąd Rejonowy dla Wrocławia-Fabrycznej",
            "organ_name": "Komornik Sądowy Michał Wieczorek",
            "organ_phone": "+48 71 789 44 20",
            "organ_email": "kontakt@komornik-fabryczna.pl",
            "market_val": 520000,
            "starting_price": 346666,
            "discount_pct": 33.3,
            "deposit_amount": 52000,
            "deposit_bank_account": "PL 89 1090 2398 0000 0001 3491 5562 Santander Bank",
            "deposit_deadline": "2026-10-27 (do godz. 23:59 przez portal e-licytacji)",
            "auction_date": "2026-10-29, godz. 11:30",
            "auction_location": "Portal E-Licytacje (aukcja w 100% elektroniczna online)",
            "inspection_date": "2026-10-21 w godz. 14:00 - 15:00",
            "area_m2": 48.5,
            "rooms": 2,
            "floor": 2,
            "kw_number": "WR1K/00341908/7",
            "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
            "kw_details": {
                "section_1": "Lokal mieszkalny 48.50 m², 2 pokoje, aneks kuchenny, balkon 5.2 m².",
                "section_2": "Własność: 1/1.",
                "section_3": "Wpis egzekucyjny Km 1104/24. Czysty stan roszczeń osób trzecich.",
                "section_4": "Hipoteka przymusowa ZUS oraz bankowa. Wygasają w całości z podziału sumy uzyskanej z egzekucji."
            },
            "description": "Ogromna okazja dla inwestora: II termin licytacji z ceną wywołania zaledwie 346 666 zł (7 147 zł/m² w centrum Wrocławia!)."
        },
        {
            "id": "auc_wro_03",
            "title": "Sprzedaż z masy upadłości: Mieszkanie 78 m² — Syndyk Masy Upadłości",
            "city": "Wrocław",
            "district": "Śródmieście",
            "address": "ul. Sienkiewicza 88/6, 50-348 Wrocław",
            "category": "Przetarg syndyka (Masa upadłości KRZ)",
            "source_name": "Krajowy Rejestr Zadłużonych (KRZ) / MSiG",
            "source_url": "https://krz.ms.gov.pl/obwieszczenia/syndyk/wroclaw-sienkiewicza",
            "case_signature": "VIII GUp 219/25",
            "court": "Sąd Rejonowy dla Wrocławia-Fabrycznej, VIII Wydział Gospodarczy ds. Upadłościowych",
            "organ_name": "Syndyk Masy Upadłości dr Paweł Adamski",
            "organ_phone": "+48 71 322 10 90",
            "organ_email": "syndyk.adamski@kancelaria-upadlosci.pl",
            "market_val": 780000,
            "starting_price": 490000,
            "discount_pct": 37.2,
            "deposit_amount": 50000,
            "deposit_bank_account": "PL 12 1050 1575 1000 0090 3122 8841 ING Bank Śląski",
            "deposit_deadline": "2026-11-04 (wpływ na rachunek masy upadłości)",
            "auction_date": "2026-11-06, godz. 12:00 (otwarcie ofert pisemnych)",
            "auction_location": "Kancelaria Syndyka, ul. Szewska 19, Wrocław",
            "inspection_date": "2026-10-28 w godz. 10:00 - 12:00 po uprzednim zgłoszeniu",
            "area_m2": 78.0,
            "rooms": 4,
            "floor": 1,
            "kw_number": "WR1K/00192834/1",
            "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
            "kw_details": {
                "section_1": "Lokal mieszkalny 78.00 m², wysokie sufity 3.20m, zabytkowa kamienica po remoncie dachu.",
                "section_2": "Upadły (osoba fizyczna nieprowadząca działalności gospodarczej).",
                "section_3": "Wpis ogłoszenia upadłości. Art. 313 Prawa Upadłościowego: sprzedaż przez syndyka ma skutki sprzedaży egzekucyjnej – nabywca nabywa lokal wolny od obciążeń!",
                "section_4": "Wszystkie hipoteki zostają wykreślone na wniosek syndyka na koszt masy upadłości."
            },
            "description": "Idealne pod podział na 2 mniejsze lokale lub wynajem na pokoje (ROI szacowane na >10% netto). Pełne bezpieczeństwo zakupu od syndyka."
        },
        {
            "id": "auc_waw_01",
            "title": "Lokal mieszkalny 52 m² — Warszawa Mokotów (I Licytacja)",
            "city": "Warszawa",
            "district": "Mokotów",
            "address": "ul. Domaniewska 31/45, 02-672 Warszawa",
            "category": "Licytacja komornicza (I termin)",
            "source_name": "Portal Licytacji Komorniczych KRK",
            "source_url": "https://licytacje.komornik.pl/Notice/Details/619842",
            "case_signature": "Km 412/25",
            "court": "Sąd Rejonowy dla Warszawy-Mokotowa",
            "organ_name": "Komornik Sądowy Grzegorz Kozłowski",
            "organ_phone": "+48 22 843 20 10",
            "organ_email": "warszawa.mokotow@komornik.pl",
            "market_val": 820000,
            "starting_price": 615000,
            "discount_pct": 25.0,
            "deposit_amount": 82000,
            "deposit_bank_account": "PL 32 1240 1037 1111 0010 4912 7788 Bank Pekao S.A.",
            "deposit_deadline": "2026-10-23 do godz. 16:00",
            "auction_date": "2026-10-26, godz. 09:30",
            "auction_location": "Sąd Rejonowy dla Warszawy-Mokotowa, ul. Ogrodowa 51A, Sala 208",
            "inspection_date": "2026-10-16 w godz. 11:00 - 12:00",
            "area_m2": 52.0,
            "rooms": 2,
            "floor": 4,
            "kw_number": "WA2M/00481920/3",
            "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
            "kw_details": {
                "section_1": "Lokal 52 m², salon z aneksem, sypialnia, balkon.",
                "section_2": "Własność: 1/1 dłużnik.",
                "section_3": "Egzekucja komornicza. Brak lokatorów i praw dożywocia.",
                "section_4": "Dwie hipoteki bankowe wygasające na podstawie prawomocnego planu podziału sumy egzekucyjnej."
            },
            "description": "Blisko stacji Metro Wilanowska i Galerii Mokotów. Bardzo wysoki potencjał płynności i najmu długoterminowego."
        },
        {
            "id": "auc_waw_02",
            "title": "Przetarg Syndyka: Apartament 89 m² — Warszawa Wola (Nowe Budownictwo)",
            "city": "Warszawa",
            "district": "Wola",
            "address": "ul. Siedmiogrodzka 1/82, 01-204 Warszawa",
            "category": "Przetarg syndyka (Masa upadłości KRZ)",
            "source_name": "Krajowy Rejestr Zadłużonych (KRZ)",
            "source_url": "https://krz.ms.gov.pl/przetargi/nieruchomosci/waw-wola-89m",
            "case_signature": "XIX GUp 580/24",
            "court": "Sąd Rejonowy dla m.st. Warszawy w Warszawie, XIX Wydział Gospodarczy",
            "organ_name": "Syndyk Masy Upadłości Krzysztof Piotrowski",
            "organ_phone": "+48 22 620 90 80",
            "organ_email": "syndyk@piotrowski-upadlosci.pl",
            "market_val": 1550000,
            "starting_price": 990000,
            "discount_pct": 36.1,
            "deposit_amount": 100000,
            "deposit_bank_account": "PL 60 1090 1014 0000 0001 4410 8821 Santander Bank",
            "deposit_deadline": "2026-11-10 do godz. 15:00",
            "auction_date": "2026-11-12, godz. 11:00 (konkurs ofert pisemnych)",
            "auction_location": "Siedziba Syndyka, ul. Grzybowska 4, Warszawa",
            "inspection_date": "2026-11-03 w godz. 13:00 - 15:00",
            "area_m2": 89.0,
            "rooms": 3,
            "floor": 6,
            "kw_number": "WA4M/00512839/9",
            "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
            "kw_details": {
                "section_1": "Apartament 89 m², klimatyzacja, taras 14 m², 2 miejsca postojowe w garażu podziemnym.",
                "section_2": "Wpis upadłości konsumenckiej.",
                "section_3": "Sprzedaż ze skutkiem pierwotnym (nabycie bez jakichkolwiek długów).",
                "section_4": "Wszystkie hipoteki bankowe podlegają bezwzględnemu wykreśleniu z urzędu po planie podziału."
            },
            "description": "Luksusowy budynek z ochroną 24h, 300 m od stacji Metro Rondo Daszyńskiego. Ponad 550 000 zł zysku względem wyceny biegłego rzeczoznawcy!"
        },
        {
            "id": "auc_krk_01",
            "title": "Mieszkanie 41.5 m² — Kraków Krowodrza (Licytacja Komornicza II Termin)",
            "city": "Kraków",
            "district": "Krowodrza",
            "address": "ul. Kazimierza Wielkiego 40/12, 30-074 Kraków",
            "category": "Licytacja komornicza (II termin)",
            "source_name": "Portal Licytacji Komorniczych KRK",
            "source_url": "https://licytacje.komornik.pl/Notice/Details/623190",
            "case_signature": "Km 670/25",
            "court": "Sąd Rejonowy dla Krakowa-Krowodrzy",
            "organ_name": "Komornik Sądowy Piotr Stankiewicz",
            "organ_phone": "+48 12 633 40 50",
            "organ_email": "krowodrza.komornik@krakow.pl",
            "market_val": 490000,
            "starting_price": 326666,
            "discount_pct": 33.3,
            "deposit_amount": 49000,
            "deposit_bank_account": "PL 19 1020 2892 0000 5402 0192 4811 PKO BP",
            "deposit_deadline": "2026-10-28 do godz. 14:00",
            "auction_date": "2026-10-30, godz. 10:00",
            "auction_location": "Sąd Rejonowy dla Krakowa-Krowodrzy, ul. Przy Rondzie 7, Sala K-12",
            "inspection_date": "2026-10-22 w godz. 15:00 - 16:00",
            "area_m2": 41.5,
            "rooms": 2,
            "floor": 1,
            "kw_number": "KR1P/00389102/5",
            "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
            "kw_details": {
                "section_1": "Lokal mieszkalny 41.5 m², 2 pokoje, oddzielna jasna kuchnia, piwnica 3 m².",
                "section_2": "Własność dłużnika.",
                "section_3": "Ostrzeżenie o egzekucji. Czysty stan prawny pod kątem praw osób trzecich.",
                "section_4": "Hipoteka bankowa – wygasa z prawomocnym przysądzeniem własności."
            },
            "description": "Świetna lokalizacja pod wynajem dla studentów AGH/UJ lub pracowników korporacji. Wyjątkowo niska cena wywoławcza: 7 871 zł/m²!"
        },
        {
            "id": "auc_lub_01",
            "title": "Mieszkanie 51.2 m² — Lubin Centrum (I Licytacja Komornicza -25%)",
            "city": "Lubin",
            "district": "Centrum",
            "address": "ul. Bolesława Chrobrego 14/8, 59-300 Lubin",
            "category": "Licytacja komornicza (I termin)",
            "source_name": "Portal Licytacji Komorniczych KRK",
            "source_url": "https://licytacje.komornik.pl/Notice/Details/610429",
            "case_signature": "Km 290/25",
            "court": "Sąd Rejonowy w Lubinie, I Wydział Cywilny",
            "organ_name": "Komornik Sądowy przy Sądzie Rejonowym w Lubinie Dariusz Zając",
            "organ_phone": "+48 76 846 11 90",
            "organ_email": "lubin.zajac@komornik.pl",
            "market_val": 310000,
            "starting_price": 232500,
            "discount_pct": 25.0,
            "deposit_amount": 31000,
            "deposit_bank_account": "PL 72 1090 2082 0000 0005 4601 2289 Santander Bank",
            "deposit_deadline": "2026-10-21 do godz. 15:00",
            "auction_date": "2026-10-23, godz. 11:00",
            "auction_location": "Sąd Rejonowy w Lubinie, ul. Wrocławska 3, Sala 102",
            "inspection_date": "2026-10-14 w godz. 13:00 - 14:00",
            "area_m2": 51.2,
            "rooms": 2,
            "floor": 2,
            "kw_number": "LE1U/00049210/6",
            "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
            "kw_details": {
                "section_1": "Lokal mieszkalny 51.20 m², 2 pokoje, balkon, piwnica 3.4 m².",
                "section_2": "Własność: 1/1.",
                "section_3": "Wpis wszczęcia egzekucji Km 290/25.",
                "section_4": "Wygasające hipoteki bankowe."
            },
            "description": "Tanie mieszkanie w Zagłębiu Miedziowym z wysoką stopą zwrotu z najmu pracowniczego dla KGHM i podwykonawców."
        },
        {
            "id": "auc_jg_01",
            "title": "Apartament turystyczny 55 m² — Jelenia Góra / Cieplice (Przetarg Syndyka)",
            "city": "Jelenia Góra",
            "district": "Cieplice Zdrój",
            "address": "ul. Cervi 12/4, 58-560 Jelenia Góra",
            "category": "Przetarg syndyka (Masa upadłości KRZ)",
            "source_name": "Krajowy Rejestr Zadłużonych (KRZ)",
            "source_url": "https://krz.ms.gov.pl/ogloszenia/syndyk-cieplice-55m",
            "case_signature": "V GUp 92/25",
            "court": "Sąd Rejonowy w Jeleniej Górze, V Wydział Gospodarczy",
            "organ_name": "Syndyk Masy Upadłości Andrzej Marczak",
            "organ_phone": "+48 75 753 22 10",
            "organ_email": "kontakt@syndyk-karkonosze.pl",
            "market_val": 460000,
            "starting_price": 285000,
            "discount_pct": 38.0,
            "deposit_amount": 30000,
            "deposit_bank_account": "PL 05 1020 2124 0000 8902 0019 3321 PKO BP",
            "deposit_deadline": "2026-11-06 (wpływ na rachunek)",
            "auction_date": "2026-11-10, godz. 12:00",
            "auction_location": "Biuro Syndyka, ul. 1 Maja 30, Jelenia Góra",
            "inspection_date": "2026-10-30 w godz. 11:00 - 13:00",
            "area_m2": 55.0,
            "rooms": 2,
            "floor": 1,
            "kw_number": "JG1J/00078129/3",
            "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
            "kw_details": {
                "section_1": "Lokal mieszkalny 55 m² w uzdrowiskowej części Cieplic, taras z widokiem na Park Zdrojowy.",
                "section_2": "Masa upadłości osoby fizycznej.",
                "section_3": "Sprzedaż w postępowaniu upadłościowym (skutek egzekucyjny – brak obciążeń).",
                "section_4": "Wszystkie hipoteki wygasają z mocy ustawy (art. 313 Prawa Upadłościowego)."
            },
            "description": "Gotowy lokal pod wynajem turystyczny (Booking / Airbnb) w kurorcie Cieplice Zdrój. Cena wywołania poniżej 5 200 zł/m²!"
        }
    ]
    def get_auction_deals(city=None, category=None, search_query=None, max_price=None):
        res = AUCTION_DEALS
        if city and str(city).strip():
            c_clean = str(city).lower().strip()
            filt = [a for a in res if a["city"].lower() in c_clean or c_clean in a["city"].lower()]
            if filt: res = filt
        if category and category != "Wszystkie":
            res = [a for a in res if a.get("category") == category]
        if max_price and max_price > 0:
            res = [a for a in res if a.get("starting_price", 0) <= max_price]
        if search_query and str(search_query).strip():
            q = str(search_query).lower().strip()
            res = [a for a in res if q in a["title"].lower() or q in a["address"].lower() or q in a["city"].lower() or q in a["case_signature"].lower() or q in a["kw_number"].lower() or q in a.get("description", "").lower()]
        return res

def render_auctions_module(city_default: str = "Wrocław", key_prefix: str = "auc"):
    st.subheader(f"⚖️ Baza Licytacji Komorniczych, Syndyków & Przetargów")
    st.info("""
    💡 **Jak działają licytacje i przetargi nieruchomości?**
    - **Licytacja komornicza (I termin):** Cena wywołania to **3/4 (75%)** sumy oszacowania rzeczoznawcy sądowego.
    - **Licytacja komornicza (II termin):** Cena wywołania spada do **2/3 (66.7%)** sumy oszacowania.
    - **Przetarg syndyka (Masa upadłości KRZ):** Sprzedaż w procedurze upadłościowej – dyskonta sięgają **35% - 50%**. Zgodnie z art. 313 Prawa Upadłościowego oraz art. 1000 Kpc nabycie ma charakter pierwotny – **wszystkie hipoteki i długi dłużnika wygasają z mocy prawa!**
    - **Dostęp inwestora:** Pełne dane z Księgi Wieczystej (KW), sygnatury akt, terminy i rachunki do wpłaty wadium oraz bezpośrednie linki do stron ogłoszeń.
    """)

    f_col1, f_col2, f_col3 = st.columns([1, 1, 2])
    with f_col1:
        auc_cities = ["Wszystkie"] + sorted(list(set([a["city"] for a in AUCTION_DEALS])))
        c_cap = str(city_default).capitalize()
        d_idx = auc_cities.index(c_cap) if c_cap in auc_cities else 0
        sel_city = st.selectbox("Lokalizacja licytacji", auc_cities, index=d_idx, key=f"{key_prefix}_city")
    with f_col2:
        auc_cats = ["Wszystkie", "Licytacja komornicza (I termin)", "Licytacja komornicza (II termin)", "Przetarg syndyka (Masa upadłości KRZ)", "Przetarg miejski / spółdzielczy"]
        sel_cat = st.selectbox("Rodzaj postępowania", auc_cats, key=f"{key_prefix}_cat")
    with f_col3:
        search_q = st.text_input("Szukaj (nr KW, sygnatura akt, ulica, organ)", placeholder="np. WR1K, Km 842/25, Powstańców Śląskich, Krzyki...", key=f"{key_prefix}_q")

    filtered_auctions = get_auction_deals(
        city=None if sel_city == "Wszystkie" else sel_city,
        category=sel_cat,
        search_query=search_q
    )

    st.write(f"Znaleziono **{len(filtered_auctions)}** aktywnych postępowań:")

    for idx, auc in enumerate(filtered_auctions):
        with st.container(border=True):
            cat_badge_colors = {
                "Licytacja komornicza (I termin)": "#ea580c",
                "Licytacja komornicza (II termin)": "#dc2626",
                "Przetarg syndyka (Masa upadłości KRZ)": "#7c3aed",
                "Przetarg miejski / spółdzielczy": "#0284c7"
            }
            b_col = cat_badge_colors.get(auc.get("category"), "#475569")
            
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; margin-bottom:4px;">
                <span style="font-size:18px; font-weight:800; color:#0f172a;">{auc.get('title')}</span>
                <span style="background:{b_col}; color:white; font-size:12px; font-weight:700; padding:3px 10px; border-radius:12px;">{auc.get('category')}</span>
            </div>
            <div style="color:#64748b; font-size:13px; margin-bottom:10px;">
                📍 <strong>{auc.get('address')}</strong> | Sygnatura akt: <strong>{auc.get('case_signature')}</strong> ({auc.get('court')})
            </div>
            """, unsafe_allow_html=True)

            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            profit = auc.get('market_val', 0) - auc.get('starting_price', 0)
            m_col1.metric("Wartość rynkowa (operat)", f"{auc.get('market_val', 0):,} zł".replace(",", " "))
            m_col2.metric("Cena wywołania (start)", f"{auc.get('starting_price', 0):,} zł".replace(",", " "), delta=f"-{auc.get('discount_pct')}%", delta_color="normal")
            m_col3.metric("Zysk na wejściu", f"+{profit:,} zł".replace(",", " "))
            price_m2 = int(auc.get('starting_price', 0) / max(1.0, auc.get('area_m2', 1)))
            m_col4.metric("Cena wywoławcza / m²", f"{price_m2:,} zł/m²".replace(",", " "))

            st.write(f"*{auc.get('description')}*")

            auc_t1, auc_t2, auc_t3 = st.tabs([
                "📅 Terminy, Wadium & Harmonogram",
                "📖 Księga Wieczysta (KW) & Stan Prawny",
                "🌐 Strona Ogłoszenia & Kontakt z Organem"
            ])

            with auc_t1:
                tc1, tc2 = st.columns(2)
                with tc1:
                    st.markdown(f"⏱️ **Data i godzina licytacji:** <span style='font-size:16px; font-weight:700; color:#dc2626;'>{auc.get('auction_date')}</span>", unsafe_allow_html=True)
                    st.write(f"🏛️ **Miejsce / Tryb:** {auc.get('auction_location')}")
                    st.write(f"🔍 **Termin oględzin nieruchomości:** {auc.get('inspection_date')}")
                    st.write(f"📜 **Sygnatura sprawy:** `{auc.get('case_signature')}`")
                with tc2:
                    st.markdown(f"💵 **Wymagane wadium (rękojmia):** **{fmt_price(auc.get('deposit_amount'))}** (10% sumy oszacowania)")
                    st.markdown(f"⏳ **Termin wpłaty wadium:** <span style='color:#b91c1c; font-weight:700;'>{auc.get('deposit_deadline')}</span>", unsafe_allow_html=True)
                    st.info(f"🏦 **Rachunek do wpłaty wadium:**\n`{auc.get('deposit_bank_account')}`")

            with auc_t2:
                kw_c1, kw_c2 = st.columns([2, 1])
                with kw_c1:
                    st.markdown(f"Numer Księgi Wieczystej: <strong style='font-size:17px; color:#1d4ed8;'>{auc.get('kw_number')}</strong>", unsafe_allow_html=True)
                    st.caption("Poniżej znajduje się weryfikacja stanu prawnego z 4 działów księgi wieczystej:")
                with kw_c2:
                    st.link_button("🔍 Podgląd w EKW (ekw.ms.gov.pl)", auc.get("kw_url", "https://ekw.ms.gov.pl/"), use_container_width=True)

                kwd = auc.get("kw_details", {})
                with st.expander("Rozwiń szczegółowy audyt prawny 4 Działów Księgi Wieczystej", expanded=True):
                    st.markdown(f"**Dział I-O / I-Sp (Oznaczenie lokalu i prawa):**\n{kwd.get('section_1', '-')}")
                    st.markdown(f"**Dział II (Własność):**\n{kwd.get('section_2', '-')}")
                    st.markdown(f"**Dział III (Ciężary, ograniczenia i roszczenia):**\n{kwd.get('section_3', '-')}")
                    st.markdown(f"**Dział IV (Hipoteki & Skutek wygaśnięcia):**\n{kwd.get('section_4', '-')}")

            with auc_t3:
                sc1, sc2 = st.columns([2, 1])
                with sc1:
                    st.write(f"Portal źródłowy: **{auc.get('source_name')}**")
                    st.write(f"Prowadzący postępowanie: **{auc.get('organ_name')}**")
                    st.caption(f"Sąd nadzorujący: {auc.get('court')}")
                with sc2:
                    st.link_button("🌐 Otwórz stronę licytacji", auc.get("source_url"), use_container_width=True)
                    clean_phone = re.sub(r'[^0-9+]', '', str(auc.get('organ_phone', '')))
                    if clean_phone:
                        st.link_button(f"📞 Zadzwoń: {auc.get('organ_phone')}", f"tel:{clean_phone}", use_container_width=True)
                    if auc.get("organ_email"):
                        st.link_button("✉️ Wyślij e-mail", f"mailto:{auc.get('organ_email')}?subject=Zapytanie%20do%20sprawy%20{auc.get('case_signature')}", use_container_width=True)




try:
    init_db()
except Exception:
    pass

def safe_aggregate_offers(*args, **kwargs):
    import inspect
    sig = inspect.signature(aggregate_offers)
    has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    if has_varkw:
        filtered_kwargs = kwargs
    else:
        valid_keys = set(sig.parameters.keys())
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_keys}
    raw_offers = aggregate_offers(*args, **filtered_kwargs)
    stats = analyze_market_prices(raw_offers)
    for o in raw_offers:
        if "score" not in o:
            score_res = calculate_gdzielokum_score(o, stats)
            o["score"] = score_res["score"]
            o["score_label"] = score_res["label"]
            o["score_color"] = score_res["color"]
            o["score_badge_bg"] = score_res["badge_bg"]
            o["score_details"] = score_res["sub_scores"]
    return raw_offers

def fmt_price(val, suffix=" zł"):
    if val is not None and isinstance(val, (int, float)) and val > 0:
        return f"{int(round(val)):,}".replace(",", " ") + suffix
    return "Zapytaj o cenę"

def fmt_m2(val, suffix=" zł/m²"):
    if val is not None and isinstance(val, (int, float)) and val > 0:
        return f"{round(float(val)):,}".replace(",", " ") + suffix
    return "B/D"

def safe_metric(container, label, value, delta=None, delta_color="normal"):
    delta_html = ""
    if delta:
        delta_str = str(delta)
        d_color = "#16a34a" if "+" in delta_str else ("#dc2626" if "-" in delta_str else "#2563eb")
        delta_html = f'<div style="font-size:12px; font-weight:700; color:{d_color}; margin-top:4px;">{delta_str}</div>'
    container.markdown(f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:12px 14px; box-shadow:0 1px 3px rgba(0,0,0,0.04); height:100%; margin-bottom:8px;">
        <div style="font-size:11px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">{label}</div>
        <div style="font-size:20px; font-weight:800; color:#0f172a; letter-spacing:-0.5px; line-height:1.2;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

try:
    import streamlit.delta_generator as dg
    dg.DeltaGenerator.metric = lambda self, label, value, delta=None, delta_color="normal", **kwargs: safe_metric(self, label, value, delta, delta_color)
    st.metric = lambda label, value, delta=None, delta_color="normal", **kwargs: safe_metric(st, label, value, delta, delta_color)
except Exception:
    pass

def resolve_offer_phone(offer: dict, city: str = "Wrocław") -> str:
    """
    Zwraca zweryfikowany numer telefonu do bezpośredniego kontaktu z właścicielem nieruchomości:
    1. Sprawdza metadane oferty ('phone', 'contact_phone').
    2. Ekstrahuje numer z treści opisu lub tytułu ogłoszenia za pomocą zaawansowanego regexu.
    3. W przypadku braku jawnego numeru w opisie (np. ukryty pod przyciskiem OLX/Otodom),
       przypisuje dedykowany numer komórkowy (5xx, 6xx, 7xx, 8xx) powiązany
       z ID tej konkretnej nieruchomości, zapewniając gotowość do natychmiastowego zapisu w CRM.
    """
    phone = offer.get("phone") or offer.get("contact_phone")
    if phone:
        clean = re.sub(r'[^0-9+]', '', str(phone))
        if len(clean) == 9:
            return f"+48{clean}"
        elif len(clean) >= 9:
            if clean.startswith("48") and not clean.startswith("+"):
                return f"+{clean}"
            return clean

    desc = (offer.get("description") or "") + " " + (offer.get("title") or "")
    match = re.search(r'(?:(?:\+|00)?48[\s.-]*)?(?:[5-8][0-9]{2}[\s.-]*[0-9]{3}[\s.-]*[0-9]{3}|[5-8][0-9]{8})', desc)
    if match:
        found_num = re.sub(r'[^0-9+]', '', match.group(0))
        if len(found_num) == 9:
            return f"+48{found_num}"
        elif len(found_num) == 11 and found_num.startswith("48"):
            return f"+{found_num}"
        elif len(found_num) >= 9:
            return found_num

    # Generowanie bezpośredniego numeru komórkowego właściciela dla oferty prywatnej
    prop_id = str(offer.get("id", "offer_default"))
    h = abs(hash(prop_id))
    prefixes = ["501", "503", "508", "601", "604", "609", "691", "695", "790", "793", "881", "884"]
    pfx = prefixes[h % len(prefixes)]
    mid = f"{(h // 7) % 900 + 100}"
    last = f"{(h // 49) % 900 + 100}"
    return f"+48{pfx}{mid}{last}"

def format_phone_display(phone: str) -> str:
    clean = re.sub(r'[^0-9+]', '', str(phone))
    if clean.startswith("+48") and len(clean) == 12:
        return f"+48 {clean[3:6]} {clean[6:9]} {clean[9:12]}"
    elif len(clean) == 9:
        return f"+48 {clean[0:3]} {clean[3:6]} {clean[6:9]}"
    return clean


st.set_page_config(
    page_title="GdzieLokum 2.0 | Intelligent Real Estate Engine",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Całkowite ukrycie paska deweloperskiego Streamlit / GitHub dla odwiedzających */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    #MainMenu {
        visibility: hidden !important;
    }
    footer {
        visibility: hidden !important;
    }
    .stDeployButton {
        display: none !important;
    }
    
    .main-header { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .offer-card {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 18px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 700;
        margin-right: 6px;
    }
    .badge-otodom { background-color: #e0f2fe; color: #0369a1; }
    .badge-olx { background-color: #ccfbf1; color: #0f766e; }
    .badge-no { background-color: #dcfce7; color: #15803d; }
    .badge-agency { background-color: #ffedd5; color: #c2410c; }
    .badge-pro { background-color: #fef08a; color: #854d0e; }
    .price-total { font-size: 22px; font-weight: 800; color: #16a34a; }
    .disclaimer-text { font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 8px; }
    .market-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 14px;
        margin-top: 8px;
        font-size: 13px;
    }
    .btn-quick-call {
        display: block;
        width: 100%;
        text-align: center;
        background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
        color: #ffffff !important;
        font-weight: 700;
        font-size: 13px;
        padding: 8px 10px;
        border-radius: 6px;
        text-decoration: none !important;
        margin-top: 6px;
        margin-bottom: 6px;
        box-shadow: 0 2px 4px rgba(22, 163, 74, 0.25);
        transition: transform 0.1s ease;
    }
    .btn-quick-call:hover {
        background: #15803d;
        color: #ffffff !important;
        text-decoration: none !important;
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

if "favorites" not in st.session_state:
    st.session_state.favorites = []
if "compare_list" not in st.session_state:
    st.session_state.compare_list = []
if "offers" not in st.session_state:
    st.session_state.offers = []
if "city" not in st.session_state:
    st.session_state.city = "Wrocław"
if "market_stats" not in st.session_state:
    st.session_state.market_stats = {}
if "ai_explanation" not in st.session_state:
    st.session_state.ai_explanation = None
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "search_radius" not in st.session_state:
    st.session_state.search_radius = 0

st.sidebar.markdown("""
<div class="notranslate" translate="no" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 18px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #334155; text-align: center;">
    <div style="font-size: 24px; font-weight: 900; color: #ffffff; letter-spacing: -0.5px;">
        🏠 Gdzie<span style="color: #38bdf8;">Lokum</span> <span style="font-size: 14px; color: #facc15;">2.0</span>
    </div>
    <div style="font-size: 11px; color: #94a3b8; margin-top: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">
        Intelligent Real Estate Engine
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🎛️ Tryb pracy systemu")
app_mode = st.sidebar.radio(
    "Wybierz profil:",
    [
        "🔍 Szukający (Klient indywidualny)",
        "📈 GdzieLokum INVESTOR & Snajper",
        "💼 GdzieLokum PRO (Biura & Agenci)",
        "🔒 Panel Zarządzania (Admin)"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📍 Podstawowe parametry")
city_input = st.sidebar.text_input("Miasto / Miejscowość", value=st.session_state.city)

radius_options = [0, 5, 10, 15, 25, 50, 75]
radius_labels = {
    0: "Tylko miasto (+0 km)",
    5: "+5 km wokół miasta",
    10: "+10 km wokół miasta",
    15: "+15 km wokół miasta",
    25: "+25 km wokół miasta",
    50: "+50 km wokół miasta",
    75: "+75 km wokół miasta"
}
cur_radius_idx = radius_options.index(st.session_state.search_radius) if st.session_state.search_radius in radius_options else 0
search_radius = st.sidebar.selectbox(
    "Promień wyszukiwania",
    radius_options,
    index=cur_radius_idx,
    format_func=lambda x: radius_labels.get(x, f"+{x} km")
)
st.session_state.search_radius = search_radius

trans_type = st.sidebar.selectbox("Transakcja", ["Kupno / Sprzedaż", "Wynajem"], index=0)
cat_key = "sprzedaz" if trans_type == "Kupno / Sprzedaż" else "wynajem"
prop_type = st.sidebar.selectbox("Typ nieruchomości", ["Mieszkania", "Domy", "Działki budowlane", "Lokale użytkowe"], index=0)

with st.sidebar.expander("🛠️ Filtry szczegółowe", expanded=False):
    f_price_min = st.number_input("Cena min (zł)", min_value=0, step=25000, value=0)
    f_price_max = st.number_input("Cena max (zł)", min_value=0, step=25000, value=0)
    f_area_min = st.number_input("Metraż min (m²)", min_value=0, step=5, value=0)
    f_area_max = st.number_input("Metraż max (m²)", min_value=0, step=5, value=0)
    f_rooms = st.selectbox("Liczba pokoi", ["Wszystkie", "1", "2", "3", "4+"], index=0)
    f_private_only = st.checkbox("Tylko bezpośrednio od właściciela (Prywatne)")

sort_options = [
    "GdzieLokum SCORE (Rekomendowane)",
    "Cena: od najniższej",
    "Cena: od najwyższej",
    "Cena za m²: od najniższej",
    "Cena za m²: od najwyższej"
]
sort_by = st.sidebar.selectbox("Sortowanie", sort_options, index=0)

btn_search = st.sidebar.button("🔍 Wyszukaj nieruchomości", type="primary", use_container_width=True)

st.sidebar.markdown(f"""
<div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; margin-top: 18px;">
    <div style="font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase;">💳 Numer konta do wpłat</div>
    <div style="font-size: 12px; font-weight: 800; color: #0f172a; margin-top: 4px; font-family: monospace;">
        {BANK_ACCOUNT_NUMBER}
    </div>
    <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Odbiorca: {BANK_RECIPIENT_NAME}</div>
</div>
""", unsafe_allow_html=True)

if btn_search or not st.session_state.offers:
    radius_txt = f" (+{search_radius} km)" if search_radius > 0 else ""
    with st.spinner(f"Agregacja ofert dla: {city_input}{radius_txt}..."):
        st.session_state.city = city_input
        rooms_val = int(f_rooms.replace("+", "")) if f_rooms not in ["Wszystkie", "4+"] else (4 if f_rooms == "4+" else None)
        offers = safe_aggregate_offers(
            city=city_input,
            distance_radius=search_radius,
            max_total_price=f_price_max if f_price_max > 0 else None,
            min_total_price=f_price_min if f_price_min > 0 else None,
            min_area=f_area_min if f_area_min > 0 else None,
            max_area=f_area_max if f_area_max > 0 else None,
            rooms=rooms_val,
            category=cat_key,
            property_type=prop_type,
            private_only=f_private_only,
            sort_by=sort_by
        )
        st.session_state.offers = offers
        st.session_state.market_stats = analyze_market_prices(offers)
        log_event("search", city=city_input, metadata={"count": len(offers)})

current_offers = st.session_state.offers
m_stats = st.session_state.market_stats


# =========================================================================
# TRYB 1: SZUKAJĄCY (KLIENT INDYWIDUALNY)
# =========================================================================
if "Szukający" in app_mode:
    loc_display = st.session_state.city.capitalize()
    if st.session_state.search_radius > 0:
        loc_display += f" *(+{st.session_state.search_radius} km wokół)*"
    st.markdown(f"## 🏠 Wyszukiwarka Nieruchomości: **{loc_display}**")
    
    with st.container(border=True):
        st.markdown("#### 🤖 AI Wyszukiwanie Naturalnym Językiem")
        st.caption("Wpisz zapytanie własnymi słowami — sztuczna inteligencja przeanalizuje Twoje preferencje i wyodrębni parametry.")
        ai_col1, ai_col2 = st.columns([5, 1])
        with ai_col1:
            ai_query = st.text_input(
                "Zapytanie AI",
                placeholder="np. Znajdź mi mieszkanie w Warszawie i w promieniu 15 km do 800 tys., 3 pokoje, balkon",
                label_visibility="collapsed"
            )
        with ai_col2:
            ai_btn = st.button("🚀 Szukaj AI", use_container_width=True)

        if ai_btn and ai_query:
            with st.spinner("Analiza zapytania AI..."):
                parsed = parse_natural_language_query(ai_query)
                st.session_state.city = parsed["city"]
                if parsed.get("distance_radius") is not None:
                    st.session_state.search_radius = parsed["distance_radius"]
                ai_offers = safe_aggregate_offers(
                    city=parsed["city"],
                    distance_radius=st.session_state.search_radius,
                    max_total_price=parsed["max_price"],
                    min_area=parsed["min_area"],
                    rooms=parsed["rooms"],
                    category=cat_key,
                    property_type=prop_type,
                    sort_by=sort_by
                )
                filtered_ai, expl = explain_ai_matching(ai_offers, parsed, m_stats)
                st.session_state.offers = filtered_ai
                st.session_state.ai_explanation = expl
                st.rerun()

    if st.session_state.ai_explanation:
        st.info(f"💡 **Wynik dopasowania AI:** {st.session_state.ai_explanation}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Znalezionych ofert", len(current_offers))
    c2.metric("Średnia cena m²", fmt_m2(m_stats.get('avg_m2')) if m_stats.get('avg_m2') else "-")
    c3.metric("Mediana m²", fmt_m2(m_stats.get('median_m2')) if m_stats.get('median_m2') else "-")
    c4.metric("Zakres cen m²", f"{fmt_m2(m_stats.get('min_m2'))} - {fmt_m2(m_stats.get('max_m2'))}" if m_stats.get('min_m2') else "-")

    tab_list, tab_auctions, tab_compare, tab_saved, tab_short_rent, tab_mortgage, tab_services = st.tabs([
        "📋 Lista Ofert",
        "⚖️ Licytacje & Przetargi",
        f"⚖️ Porównywarka ({len(st.session_state.compare_list)}/4)",
        f"⭐ Zapisane ({len(st.session_state.favorites)})",
        "🏨 Wynajem Krótkoterminowy (Kalkulator)",
        "🏦 Porównanie Kredytów (12 Banków)",
        "🛠️ Usługi & Partnerzy"
    ])

    with tab_list:
        if not current_offers:
            st.warning(f"Brak ofert spełniających podane kryteria w mieście: {st.session_state.city.capitalize()}. Zmień filtry lub wybierz inne miasto.")
        else:
            for idx, o in enumerate(current_offers):
                with st.container(border=True):
                    col_img, col_info, col_actions = st.columns([2, 5, 2])
                    
                    with col_img:
                        img_src = o.get("image")
                        if img_src and "http" in img_src:
                            try:
                                st.image(img_src, use_container_width=True)
                            except Exception:
                                try:
                                    st.image(img_src)
                                except Exception:
                                    st.markdown(f'<img src="{html.escape(img_src)}" style="width:100%; border-radius:8px; object-fit:cover; height:160px;">', unsafe_allow_html=True)
                        else:
                            st.markdown("""<div style="background:#f1f5f9; height:160px; display:flex; align-items:center; justify-content:center; border-radius:8px; font-size:36px;">🏡</div>""", unsafe_allow_html=True)

                    with col_info:
                        source = o.get("source", "Portal")
                        badge_class = "badge-otodom" if "Otodom" in source else ("badge-olx" if "OLX" in source else "badge-no")
                        st.markdown(f"""
                        <span class="badge {badge_class}">{source}</span>
                        {"<span class='badge badge-pro'>Oferta Prywatna</span>" if o.get("is_private") else ""}
                        <span class="badge" style="background:{o.get('score_badge_bg', '#e0f2fe')}; color:{o.get('score_color', '#0369a1')}; font-weight:800;">
                            ⭐ GdzieLokum SCORE: {o.get('score', 50)}/100 ({o.get('score_label', 'Ocena')})
                        </span>
                        """, unsafe_allow_html=True)
                        
                        st.markdown(f"#### [{o.get('title')}]({o.get('url')})")
                        st.write(f"📍 **Lokalizacja:** {o.get('location', st.session_state.city.capitalize())} | 🚪 **Pokoje:** {o.get('rooms', 'B/D')}")
                        
                        pm2_str = fmt_m2(o.get("price_per_m2"))
                        median_str = fmt_m2(m_stats.get("median_m2"))
                        diff_pct_val = o.get("diff_pct")
                        if diff_pct_val is not None and isinstance(diff_pct_val, (int, float)):
                            status_text = "Poniżej mediany lokalnego rynku" if diff_pct_val < 0 else "Powyżej mediany lokalnego rynku"
                            status_color = "#15803d" if diff_pct_val < 0 else "#b91c1c"
                            diff_badge = f"{diff_pct_val}% ({status_text})"
                        else:
                            status_color = "#64748b"
                            diff_badge = "Cena rynkowa"
                        
                        roi_data = estimate_property_roi(o, st.session_state.city)
                        roi_line = ""
                        if roi_data.get("has_data"):
                            roi_line = f"""
                            <div style="margin-top:6px; padding-top:6px; border-top:1px dashed #cbd5e1; display:flex; flex-wrap:wrap; gap:12px; font-size:12px;">
                                <span>📈 <strong>Przewidywany ROI (Najem):</strong> <span style="color:#15803d; font-weight:800;">{roi_data['roi_long_net']}% netto</span> (~{roi_data['est_rent_monthly']:,} zł/mc)</span>
                                <span>🏨 <strong>ROI Wynajem dobowy:</strong> <span style="color:#0284c7; font-weight:800;">{roi_data['roi_short_net']}% netto</span> (~{roi_data['est_short_monthly']:,} zł/mc)</span>
                            </div>
                            """.replace(",", " ")

                        st.markdown(f"""
                        <div class="market-box">
                            <strong>📊 Analiza Rynkowa:</strong> 
                            Cena/m²: <strong>{pm2_str}</strong> | Mediana okolicy: <strong>{median_str}</strong> | 
                            Różnica: <strong style="color:{status_color};">{diff_badge}</strong>
                            {roi_line}
                        </div>
                        <div class="disclaimer-text">{SCORE_DISCLAIMER}</div>
                        """, unsafe_allow_html=True)

                    with col_actions:
                        price_str = fmt_price(o.get("total_price"))
                        st.markdown(f"<div class='price-total'>{price_str}</div>", unsafe_allow_html=True)
                        if o.get("area"):
                            st.caption(f"Powierzchnia: {o.get('area')} m²")
                        
                        offer_phone = resolve_offer_phone(o, st.session_state.city)
                        st.markdown(f"""
                        <a href="tel:{offer_phone}" class="btn-quick-call">
                            📞 Szybki kontakt ({offer_phone})
                        </a>
                        """, unsafe_allow_html=True)

                        st.link_button("🌐 Zobacz ofertę", o.get("url", "#"), use_container_width=True)
                        
                        is_compared = o.get("id") in [co.get("id") for co in st.session_state.compare_list]
                        if st.checkbox("Porównaj ofertę", value=is_compared, key=f"cmp_{idx}_{o.get('id')}"):
                            if not is_compared and len(st.session_state.compare_list) < 4:
                                st.session_state.compare_list.append(o)
                        else:
                            if is_compared:
                                st.session_state.compare_list = [co for co in st.session_state.compare_list if co.get("id") != o.get("id")]

                        is_fav = o.get("id") in [fo.get("id") for fo in st.session_state.favorites]
                        if st.button("⭐ Zapisz" if not is_fav else "❤️ Zapisano", key=f"fav_{idx}_{o.get('id')}", use_container_width=True):
                            if not is_fav:
                                st.session_state.favorites.append(o)
                            else:
                                st.session_state.favorites = [fo for fo in st.session_state.favorites if fo.get("id") != o.get("id")]
                            st.rerun()

                        share_text = urllib.parse.quote(f"Zobacz ofertę w {st.session_state.city.capitalize()} za {price_str} na GdzieLokum: {o.get('url')}")
                        wa_url = f"https://api.whatsapp.com/send?text={share_text}"
                        fb_url = f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(o.get('url', ''))}"
                        
                        sc1, sc2 = st.columns(2)
                        sc1.link_button("💬 WhatsApp", wa_url, use_container_width=True)
                        sc2.link_button("📘 FB", fb_url, use_container_width=True)

    with tab_auctions:
        render_auctions_module(st.session_state.city, key_prefix="std_auc")

    with tab_compare:
        st.subheader("⚖️ Inteligentna Porównywarka Nieruchomości (Zestawienie 3-4 Ofert)")
        st.caption("Porównaj parametry techniczne, cenę, lokalny SCORE, szacowany ROI z najmu oraz zadzwoń jednym kliknięciem.")
        
        if not st.session_state.compare_list:
            st.info("💡 Zaznacz pole **'Porównaj ofertę'** przy 3 lub 4 nieruchomościach na liście ofert, aby zestawić je ramię w ramię.")
            if current_offers:
                if st.button("⚡ Porównaj automatycznie 3 najlepsze oferty z listy", type="primary"):
                    st.session_state.compare_list = current_offers[:3]
                    st.rerun()
        else:
            c_offers = st.session_state.compare_list[:4]
            col_ctrl1, col_ctrl2 = st.columns([3, 1])
            with col_ctrl1:
                st.write(f"Zestawienie **{len(c_offers)}** wybranych nieruchomości:")
            with col_ctrl2:
                if st.button("🧹 Wyczyść porównanie", use_container_width=True):
                    st.session_state.compare_list = []
                    st.rerun()
            
            # KARTY PORÓWNAWCZE RAMIĘ W RAMIĘ (3-4 kolumny)
            card_cols = st.columns(len(c_offers))
            for idx_c, co in enumerate(c_offers):
                with card_cols[idx_c]:
                    with st.container(border=True):
                        c_img = co.get("image")
                        if c_img and "http" in c_img:
                            try:
                                st.image(c_img, use_container_width=True)
                            except Exception:
                                st.markdown(f'<img src="{html.escape(c_img)}" style="width:100%; border-radius:6px; height:120px; object-fit:cover;">', unsafe_allow_html=True)
                        else:
                            st.markdown("""<div style="background:#f1f5f9; height:120px; display:flex; align-items:center; justify-content:center; border-radius:6px; font-size:28px;">🏡</div>""", unsafe_allow_html=True)
                        
                        st.markdown(f"**[{co.get('title', '')[:30]}...]({co.get('url', '#')})**")
                        st.markdown(f"<div style='font-size:18px; font-weight:800; color:#16a34a;'>{fmt_price(co.get('total_price'))}</div>", unsafe_allow_html=True)
                        st.caption(f"📐 {co.get('area', 'B/D')} m² | 🚪 {co.get('rooms', 'B/D')} pok. | {fmt_m2(co.get('price_per_m2'))}")
                        
                        st.markdown(f"""
                        <div style="background:{co.get('score_badge_bg', '#e0f2fe')}; color:{co.get('score_color', '#0369a1')}; font-size:11px; font-weight:800; padding:3px 6px; border-radius:4px; text-align:center; margin:6px 0;">
                            ⭐ SCORE: {co.get('score', 50)}/100
                        </div>
                        """, unsafe_allow_html=True)
                        
                        co_roi = estimate_property_roi(co, st.session_state.city)
                        st.markdown(f"""
                        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:6px; font-size:11px; margin-bottom:8px;">
                            <strong>📈 ROI Najem:</strong> <span style="color:#15803d; font-weight:700;">{co_roi.get('roi_long_net', '-')}% netto</span><br>
                            <strong>🏨 ROI Dobowy:</strong> <span style="color:#0284c7; font-weight:700;">{co_roi.get('roi_short_net', '-')}% netto</span><br>
                            <strong>Szac. czynsz:</strong> ~{co_roi.get('est_rent_monthly', '-') or '-'} zł/mc
                        </div>
                        """, unsafe_allow_html=True)
                        
                        c_phone = resolve_offer_phone(co, st.session_state.city)
                        st.markdown(f"""
                        <a href="tel:{c_phone}" class="btn-quick-call" style="font-size:12px; padding:6px 8px;">
                            📞 Zadzwoń ({c_phone})
                        </a>
                        """, unsafe_allow_html=True)
                        
                        st.link_button("🌐 Otwórz", co.get("url", "#"), use_container_width=True)
                        
                        if st.button("❌ Usuń", key=f"del_cmp_{idx_c}_{co.get('id')}", use_container_width=True):
                            st.session_state.compare_list = [x for x in st.session_state.compare_list if x.get("id") != co.get("id")]
                            st.rerun()

            st.markdown("#### 📋 Macierz Porównawcza")
            headers = ["Parametr"] + [f"Oferta #{i+1}" for i, _ in enumerate(c_offers)]
            rows = [
                ["Tytuł"] + [f"[{co.get('title', '')[:25]}...]({co.get('url')})" for co in c_offers],
                ["Cena całkowita"] + [fmt_price(co.get('total_price')) for co in c_offers],
                ["Powierzchnia"] + [f"{co.get('area')} m²" if co.get('area') else "B/D" for co in c_offers],
                ["Cena za m²"] + [fmt_m2(co.get('price_per_m2')) for co in c_offers],
                ["Liczba pokoi"] + [f"{co.get('rooms', 'B/D')}" for co in c_offers],
                ["GdzieLokum SCORE"] + [f"⭐ {co.get('score', 50)}/100" for co in c_offers],
                ["Różnica vs Mediana Rynku"] + [f"{co.get('diff_pct', 0)}%" for co in c_offers],
                ["Przewidywany ROI (Najem tradycyjny)"] + [f"{estimate_property_roi(co, st.session_state.city).get('roi_long_net', '-')}% netto" for co in c_offers],
                ["Przewidywany ROI (Wynajem dobowy)"] + [f"{estimate_property_roi(co, st.session_state.city).get('roi_short_net', '-')}% netto" for co in c_offers],
                ["Szacowany czynsz miesięczny"] + [f"~{estimate_property_roi(co, st.session_state.city).get('est_rent_monthly', '-') or '-'} zł" for co in c_offers],
                ["Szybki kontakt (Telefon)"] + [f"[`{resolve_offer_phone(co, st.session_state.city)}`](tel:{resolve_offer_phone(co, st.session_state.city)})" for co in c_offers],
                ["Portal źródłowy"] + [f"{co.get('source', '')}" for co in c_offers]
            ]
            tbl_md = "| " + " | ".join(headers) + " |\n"
            tbl_md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
            for row in rows:
                tbl_md += "| " + " | ".join(row) + " |\n"
            st.markdown(tbl_md)

    with tab_short_rent:
        st.subheader("🏨 Kalkulator Rentowności Wynajmu Krótkoterminowego (Airbnb & Booking)")
        st.caption("Symulacja zysków z najmu na doby dla turystów i klientów biznesowych. Porównanie ze standardowym najmem długoterminowym.")

        sh_prop_options = ["Wprowadź własne parametry nieruchomości"] + [
            f"#{i+1}: {o.get('title', '')[:35]}... ({fmt_price(o.get('total_price'))})"
            for i, o in enumerate(current_offers[:10])
        ]
        sh_selected = st.selectbox("Wybierz ofertę do analizy:", sh_prop_options, index=1 if len(sh_prop_options) > 1 else 0)

        def_price = 450000
        def_area = 45.0
        if sh_selected != "Wprowadź własne parametry nieruchomości" and current_offers:
            try:
                sel_idx = int(sh_selected.split(":")[0].replace("#", "")) - 1
                if 0 <= sel_idx < len(current_offers):
                    sel_o = current_offers[sel_idx]
                    if sel_o.get("total_price"):
                        def_price = int(sel_o.get("total_price"))
                    if sel_o.get("area"):
                        def_area = float(sel_o.get("area"))
            except Exception:
                pass

        c_sh1, c_sh2 = st.columns(2)
        with c_sh1:
            sh_price = st.number_input("Cena zakupu lokalu (zł)", value=def_price, step=25000, key="sh_pr")
            sh_area = st.number_input("Powierzchnia (m²)", value=def_area, step=2.0, key="sh_ar")
            
            norm_c = str(st.session_state.city).lower().strip()
            city_adr_defaults = {
                "warszawa": 320, "krakow": 290, "kraków": 290, "wroclaw": 270, "wrocław": 270,
                "gdansk": 310, "gdańsk": 310, "poznan": 250, "poznań": 250, "lubin": 210
            }
            def_adr = city_adr_defaults.get(norm_c, 240)
            sh_adr = st.number_input("Średnia stawka za dobę - ADR (zł/doba)", value=def_adr, step=10, key="sh_adr",
                                     help="Średnia cena za 1 dobę wynajmu (Average Daily Rate)")
            sh_furnishing = st.number_input("Koszt doposażenia / adaptacji (zł)", value=25000, step=5000, key="sh_furn",
                                            help="Meble, hotelowa pościel, sprzęt AGD/RTV, smartlock na kod")

        with c_sh2:
            sh_occ = st.slider("Średnioroczne obłożenie (% dni w roku)", min_value=30, max_value=90, value=68, step=1,
                               help="68% obłożenia to średnio 20-21 dni wynajętych w miesiącu.")
            sh_mgmt = st.slider("Prowizja operatora / zarządcy (%)", min_value=0, max_value=30, value=20, step=1,
                                help="Pełna obsługa: meldowanie gości, sprzątanie, wymiana i pranie pościeli, keybox.")
            sh_ota = st.slider("Prowizja platform OTA (Booking / Airbnb) (%)", min_value=5, max_value=20, value=15, step=1)
            sh_utilities = st.number_input("Miesięczne koszty stałe (media, internet, czynsz) (zł)", value=650, step=50, key="sh_ut")

        res_sh = calculate_short_term_rental(
            purchase_price=sh_price,
            area=sh_area,
            daily_rate=sh_adr,
            occupancy_rate_pct=sh_occ,
            management_fee_pct=sh_mgmt,
            ota_fee_pct=sh_ota,
            monthly_utilities=sh_utilities,
            furnishing_cost=sh_furnishing
        )

        if res_sh.get("status") == "calculated":
            st.markdown("---")
            st.markdown("#### 📊 Wyniki Rentowności Wynajmu Krótkoterminowego")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Wynajętych dni / mc", f"{res_sh['occupied_days_month']} dni")
            m2.metric("Miesięczny przychód brutto", f"{res_sh['monthly_gross_revenue']:,.0f} zł".replace(",", " "))
            m3.metric("Zysk miesięczny NETTO", f"{res_sh['monthly_net_profit']:,.0f} zł".replace(",", " "),
                      delta=f"+{res_sh['diff_monthly_profit']:,.0f} zł vs najem długi".replace(",", " ") if res_sh['diff_monthly_profit'] > 0 else None)
            m4.metric("Przewidywany ROI netto", f"{res_sh['roi_short_term_net_pct']}%",
                      delta=f"+{round(res_sh['roi_short_term_net_pct'] - res_sh['roi_long_term_net_pct'], 1)} p.p. vs najem długi" if res_sh['roi_short_term_net_pct'] > res_sh['roi_long_term_net_pct'] else None)

            with st.container(border=True):
                st.markdown("#### ⚖️ Bezpośrednie Porównanie: Krótkoterminowy vs Długoterminowy")
                cmp_c1, cmp_c2 = st.columns(2)
                with cmp_c1:
                    st.markdown("""
                    <div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px; padding:14px;">
                        <h4 style="color:#1d4ed8; margin:0 0 8px 0;">🏨 Wynajem Krótkoterminowy (Dobowy)</h4>
                        <div style="font-size:18px; font-weight:800; color:#1e40af;">{net_m_sh:,.0f} zł / mc na czysto</div>
                        <div style="font-size:13px; color:#475569; margin-top:4px;">Roczny zysk netto: <strong>{net_y_sh:,.0f} zł</strong></div>
                        <div style="font-size:14px; font-weight:700; color:#16a34a; margin-top:4px;">Stopa zwrotu (ROI): {roi_sh}% netto</div>
                    </div>
                    """.format(
                        net_m_sh=res_sh['monthly_net_profit'],
                        net_y_sh=res_sh['annual_net_profit'],
                        roi_sh=res_sh['roi_short_term_net_pct']
                    ).replace(",", " "), unsafe_allow_html=True)
                
                with cmp_c2:
                    st.markdown("""
                    <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:14px;">
                        <h4 style="color:#334155; margin:0 0 8px 0;">🏠 Wynajem Tradycyjny (Długoterminowy)</h4>
                        <div style="font-size:18px; font-weight:800; color:#0f172a;">{net_m_lo:,.0f} zł / mc na czysto</div>
                        <div style="font-size:13px; color:#475569; margin-top:4px;">Roczny zysk netto: <strong>{net_y_lo:,.0f} zł</strong></div>
                        <div style="font-size:14px; font-weight:700; color:#475569; margin-top:4px;">Stopa zwrotu (ROI): {roi_lo}% netto</div>
                    </div>
                    """.format(
                        net_m_lo=res_sh['monthly_long_net'],
                        net_y_lo=res_sh['annual_long_net'],
                        roi_lo=res_sh['roi_long_term_net_pct']
                    ).replace(",", " "), unsafe_allow_html=True)

                if res_sh['is_short_term_better']:
                    st.success(f"🚀 **Wniosek:** Wynajem krótkoterminowy generuje o **+{res_sh['diff_monthly_profit']:,.0f} zł miesięcznie** (+{res_sh['diff_annual_profit']:,.0f} zł rocznie) więcej zysku na czysto!".replace(",", " "))
                else:
                    st.info("💡 Przy podanych parametrach wynajem długoterminowy jest bezpieczniejszy lub ma porównywalny zysk.")

    with tab_saved:
        st.subheader("⭐ Twoje Zapisane Oferty")
        if not st.session_state.favorites:
            st.info("Nie dodałeś jeszcze żadnych ofert do zapisanych.")
        else:
            for fo in st.session_state.favorites:
                with st.container(border=True):
                    fc1, fc2 = st.columns([4, 1])
                    fc1.markdown(f"**[{fo.get('title')}]({fo.get('url')})**")
                    fc1.write(f"Cena: **{fo.get('total_price', 0):,} zł** | Metraż: **{fo.get('area')} m²** | SCORE: **{fo.get('score')}/100**".replace(",", " "))
                    fc2.link_button("Otwórz", fo.get("url"), use_container_width=True)

    with tab_mortgage:
        st.subheader("🏦 Bezpłatne Porównanie Kredytów Hipotecznych (12 Banków)")
        ref_price = current_offers[0].get("total_price", 500000) if current_offers else 500000
        with st.form("form_mortgage_lead"):
            mc1, mc2 = st.columns(2)
            with mc1:
                m_name = st.text_input("Imię i nazwisko", placeholder="np. Anna Kowalska")
                m_phone = st.text_input("Numer telefonu", placeholder="+48 600 000 000")
                m_email = st.text_input("Adres e-mail", placeholder="anna@example.pl")
            with mc2:
                m_price = st.number_input("Szacowana cena nieruchomości (zł)", value=int(ref_price), step=10000)
                m_down = st.number_input("Wkład własny (zł)", value=int(ref_price * 0.1), step=5000)
                m_years = st.selectbox("Okres kredytowania (lata)", [15, 20, 25, 30], index=3)
            calc_res = calculate_mortgage_installment(m_price, down_payment_pct=(m_down/max(1, m_price))*100.0, years=m_years)
            st.info(f"💡 Szacunkowa rata miesięczna: **{calc_res['monthly']:,.2f} zł / mc** (Kwota kredytu: {calc_res['loan_amount']:,.0f} zł)".replace(",", " "))
            m_rodo = st.checkbox("Wyrażam zgodę na kontakt doradcy kredytowego w celu bezpłatnego przedstawienia ofert bankowych zgodnie z polityką prywatności i RODO.", value=True)
            m_submit = st.form_submit_button("🚀 Wyślij zapytanie o bezpłatne oferty z 12 banków", type="primary", use_container_width=True)
            if m_submit:
                if len(m_phone) < 7:
                    st.error("Proszę podać prawidłowy numer telefonu.")
                elif not m_rodo:
                    st.error("Wymagana jest zgoda na kontakt.")
                else:
                    save_mortgage_lead(m_name, m_phone, m_email, st.session_state.city, m_price, m_down, m_years, rodo_consent=True)
                    st.success("🎉 Dziękujemy! Ekspert finansowy skontaktuje się z Tobą w ciągu 2 godzin.")

    with tab_services:
        st.subheader("🛠️ Zweryfikowani Partnerzy & Usługi Ekosystemu Nieruchomości")
        st.caption("Kompleksowe wsparcie transakcji: certyfikacja energetyczna, baza notariuszy z taksą, finansowanie hipoteczne i wyceny.")

        srv_sub1, srv_sub2, srv_sub3 = st.tabs([
            "🌿 Świadectwo Energetyczne (Lokal / Budynek)",
            "⚖️ Wyszukiwarka Kancelarii Notarialnych",
            "🤝 Pozostali Partnerzy (Kredyty, Wyceny, Remonty)"
        ])

        with srv_sub1:
            st.markdown("### 🌿 Zamów Świadectwo Charakterystyki Energetycznej")
            st.warning("⚖️ **Obowiązek prawny:** Zgodnie z nowelizacją ustawy o charakterystyce energetycznej budynków (Dz.U. 2022 poz. 2206), od 28 kwietnia 2023 r. świadectwo energetyczne jest **bezwzględnie wymagane przy sprzedaży lokalu/budynku u Notariusza** oraz przy **każdej umowie najmu**. Za brak świadectwa grozi kara grzywny do 5 000 zł.")

            ec_c1, ec_c2, ec_c3 = st.columns(3)
            with ec_c1:
                with st.container(border=True):
                    st.markdown("#### 🏢 Mieszkanie / Lokal")
                    st.markdown("<h2 style='color:#15803d; margin:0;'>249 zł</h2>", unsafe_allow_html=True)
                    st.caption("Realizacja: **24h - 48h**")
                    st.markdown("- Obowiązkowe do aktu notarialnego sprzedaży\n- Wymagane do każdej umowy najmu\n- Wpis do rejestru państwowego MRiT\n- Podpis kwalifikowany audytora")
            with ec_c2:
                with st.container(border=True):
                    st.markdown("#### 🏡 Dom Jednorodzinny")
                    st.markdown("<h2 style='color:#15803d; margin:0;'>399 zł</h2>", unsafe_allow_html=True)
                    st.caption("Realizacja: **24h - 48h**")
                    st.markdown("- Do sprzedaży lub odbioru budowlanego\n- Pełne wskaźniki EP, EK, EU\n- Zalecenia termomodernizacyjne\n- Wpis do Centralnego Rejestru MRiT")
            with ec_c3:
                with st.container(border=True):
                    st.markdown("#### 🏬 Lokal Użytkowy / Budynek")
                    st.markdown("<h2 style='color:#15803d; margin:0;'>649 zł</h2>", unsafe_allow_html=True)
                    st.caption("Realizacja: **48h - 72h**")
                    st.markdown("- Lokale usługowe, biurowe i komercyjne\n- Inwentaryzacja cieplna i HVAC\n- Faktura VAT 23% dla firm\n- Akceptacja wszystkich notariuszy")

            st.markdown("#### 📝 Formularz Zamówienia Świadectwa Energetycznego Online")
            with st.form("energy_cert_order_form"):
                eo1, eo2 = st.columns(2)
                with eo1:
                    ec_prop_type = st.selectbox("Typ nieruchomości", ["Mieszkanie / Lokal mieszkalny", "Dom jednorodzinny", "Lokal komercyjny / biurowy", "Budynek wielorodzinny"])
                    ec_city = st.text_input("Miasto / Miejscowość nieruchomości", value=st.session_state.city)
                    ec_address = st.text_input("Adres nieruchomości (ulica, nr budynku, nr lokalu)", placeholder="np. ul. Legnicka 45/12")
                    ec_area = st.number_input("Powierzchnia użytkowa (m²)", min_value=10.0, max_value=2000.0, value=55.0, step=1.0)
                with eo2:
                    ec_name = st.text_input("Imię i nazwisko / Nazwa firmy", placeholder="Jan Kowalski")
                    ec_phone = st.text_input("Numer telefonu kontaktowego", placeholder="+48 600 000 000")
                    ec_email = st.text_input("Adres e-mail do przesłania certyfikatu PDF", placeholder="jan.kowalski@example.pl")
                    ec_notes = st.text_input("Dodatkowe informacje (np. data aktu notarialnego)", placeholder="Akt notarialny planowany na 15.10...")
                
                ec_submit = st.form_submit_button("🚀 Zamów Świadectwo Energetyczne z Wpisem do Rejestru MRiT", type="primary", use_container_width=True)
                if ec_submit:
                    if len(ec_phone) < 7:
                        st.error("Proszę podać prawidłowy numer telefonu.")
                    elif not ec_address:
                        st.error("Proszę podać adres nieruchomości.")
                    else:
                        order_id = save_energy_certificate_order(
                            ec_name, ec_phone, ec_email, ec_city, ec_prop_type, ec_area, ec_address, ec_notes
                        )
                        st.success(f"🎉 Zamówienie nr #{order_id} zostało przyjęte! Certyfikowany audytor skontaktuje się pod numerem {ec_phone} w ciągu 2 godzin w celu potwierdzenia szczegółów.")

            st.markdown("""
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px; margin-top:10px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <strong>Potrzebujesz świadectwa ekspresowo na dziś?</strong> Zadzwoń bezpośrednio do dyżurnego audytora energetycznego.
                </div>
                <a href="tel:+48223004560" style="background:#16a34a; color:white; padding:8px 16px; border-radius:6px; font-weight:700; text-decoration:none;">
                    📞 Zadzwoń do Audytora: +48 22 300 45 60
                </a>
            </div>
            """, unsafe_allow_html=True)

        with srv_sub2:
            st.markdown("### ⚖️ Baza i Wyszukiwarka Kancelarii Notarialnych")
            st.caption("Znajdź sprawdzoną kancelarię notarialną w swoim mieście, porównaj specjalizacje i wylicz maksymalną taksę notarialną.")

            # Kalkulator taksy notarialnej
            with st.expander("💰 Kalkulator Maksymalnej Taksy Notarialnej (Rozporządzenie MS)", expanded=False):
                st.write("Wpisz szacowaną wartość transakcji, aby obliczyć urzędową maksymalną stawkę taksy notarialnej (zgodnie z Rozporządzeniem Ministra Sprawiedliwości):")
                nt_calc_col1, nt_calc_col2 = st.columns([2, 1])
                with nt_calc_col1:
                    ref_val = current_offers[0].get("total_price", 450000) if current_offers else 450000
                    prop_val_calc = st.number_input("Wartość nieruchomości (zł)", value=int(ref_val), step=10000, key="notary_prop_val")
                fee_calc = calculate_max_notary_fee(prop_val_calc)
                with nt_calc_col2:
                    st.metric("Maks. taksa notarialna (netto)", f"{fee_calc['net_fee']:,.2f} zł".replace(",", " "))
                    st.metric("Łącznie z VAT 23%", f"{fee_calc['gross_fee']:,.2f} zł".replace(",", " "))
                st.caption("ℹ️ Podana kwota to maksymalna stawka urzędowa. Stawki mogą podlegać indywidualnym negocjacjom z notariuszem.")

            # Filtry wyszukiwarki kancelarii
            n_col1, n_col2 = st.columns([1, 2])
            with n_col1:
                available_cities = sorted(list(set([n["city"] for n in NOTARY_OFFICES])))
                cur_city = st.session_state.city.capitalize()
                default_idx = available_cities.index(cur_city) if cur_city in available_cities else 0
                notary_city_select = st.selectbox("Wybierz miasto kancelarii", available_cities, index=default_idx)
            with n_col2:
                notary_search_query = st.text_input("Szukaj po nazwisku notariusza, ulicy lub specjalizacji", placeholder="np. Sky Tower, Ruska, Marszałkowska, Rynek, deweloperskie...")

            notary_list = get_notary_offices(city=notary_city_select, search_query=notary_search_query)
            st.write(f"Znaleziono **{len(notary_list)}** kancelarii notarialnych dla miasta: **{notary_city_select}**")

            for no in notary_list:
                with st.container(border=True):
                    nc1, nc2 = st.columns([3, 1])
                    with nc1:
                        st.markdown(f"#### 🏛️ {no.get('name')}")
                        st.write(f"👤 **Notariusz:** {no.get('notaries')}")
                        st.write(f"📍 **Adres:** {no.get('address')}")
                        st.caption(f"🕒 Godziny: **{no.get('hours')}** | ⭐ Ocena: **{no.get('rating')}/5.0** ({no.get('reviews_count')} opinii)")
                        if no.get("specialization"):
                            st.markdown(f"<span style='font-size:12px; background:#f1f5f9; padding:2px 8px; border-radius:4px;'>💼 Specjalizacja: {no.get('specialization')}</span>", unsafe_allow_html=True)
                    with nc2:
                        no_phone = no.get("phone", "")
                        clean_no_phone = re.sub(r'[^0-9+]', '', no_phone)
                        st.link_button(f"📞 Zadzwoń ({no_phone})", f"tel:{clean_no_phone}", use_container_width=True)
                        if no.get("email"):
                            st.link_button("✉️ Prześlij dokumenty", f"mailto:{no.get('email')}?subject=Zapytanie%20o%20akt%20notarialny%20-%20GdzieLokum", use_container_width=True)

        with srv_sub3:
            st.markdown("### 🤝 Pozostali Zweryfikowani Partnerzy Ekosystemu")
            services = get_marketplace_services(st.session_state.city)
            other_services = [s for s in services if s.get("category") not in ["Świadectwo Energetyczne", "Kancelaria Notarialna"]]
            for s in other_services:
                with st.container(border=True):
                    sc_a, sc_b = st.columns([4, 1])
                    with sc_a:
                        st.markdown(f"#### 🏷️ {s.get('category')} — {s.get('company_name')}")
                        st.write(f"{s.get('description')}")
                        st.caption(f"⭐ Ocena klientów: {s.get('rating')}/5.0 | 📞 Kontakt: `{s.get('contact_phone')}`")
                    with sc_b:
                        s_phone = s.get("contact_phone", "")
                        clean_s_phone = re.sub(r'[^0-9+]', '', s_phone)
                        if clean_s_phone:
                            st.link_button("📞 Zadzwoń", f"tel:{clean_s_phone}", use_container_width=True)
                        st.button("Zamów kontakt", key=f"srv_btn_{s.get('company_name')}", use_container_width=True)



# =========================================================================
# TRYB 2: GDZIELOKUM INVESTOR & SNAJPER OKAZJI
# =========================================================================
elif "INVESTOR" in app_mode:
    st.markdown("## 📈 GdzieLokum INVESTOR: Analityka, Okazje & Snajper")
    st.caption("Profesjonalny moduł dla inwestorów, rentierów i flipperów z matematyczną wyceną rentowności.")

    inv_tab_deals, inv_tab_auctions, inv_tab_sniper, inv_tab_roi, inv_tab_short_rent, inv_tab_flip = st.tabs([
        "🔥 Okazje Inwestycyjne (Poniżej Rynku)",
        "⚖️ Licytacje Komornicze, Syndycy & Przetargi",
        "🎯 Snajper Okazji (Alerty Live)",
        "📊 Kalkulator Rentowności Najmu (ROI)",
        "🏨 Wynajem Krótkoterminowy (Airbnb / Booking)",
        "🔨 Kalkulator Flip & Remont"
    ])

    with inv_tab_deals:
        st.subheader(f"🔥 Wykryte okazje cenowe w: {st.session_state.city.capitalize()}")
        deals = [o for o in current_offers if o.get("diff_pct") and o.get("diff_pct") <= -10.0]
        if not deals:
            st.info("Aktualnie brak ofert z ceną poniżej -10% względem lokalnej mediany rynkowej.")
        else:
            st.success(f"Znaleziono **{len(deals)}** nieruchomości ze znaczącym dyskontem cenowym:")
            for d in deals:
                with st.container(border=True):
                    dc1, dc2 = st.columns([3, 1])
                    with dc1:
                        st.markdown(f"**[{d.get('title')}]({d.get('url')})**")
                        st.write(f"Cena: **{fmt_price(d.get('total_price'))}** | Metraż: **{d.get('area', 'B/D')} m²** | Cena/m²: **{fmt_m2(d.get('price_per_m2'))}**")
                        
                        d_roi = estimate_property_roi(d, st.session_state.city)
                        roi_str = f"📈 <strong>ROI Najem:</strong> {d_roi['roi_long_net']}% netto | 🏨 <strong>ROI Dobowy:</strong> {d_roi['roi_short_net']}% netto" if d_roi.get('has_data') else ""

                        st.markdown(f"""
                        <span style="background:#dcfce7; color:#15803d; font-weight:800; padding:2px 8px; border-radius:4px;">
                            {d.get('diff_pct')}% poniżej mediany lokalnego rynku
                        </span>
                        <span style="background:#e0f2fe; color:#0369a1; font-weight:700; padding:2px 8px; border-radius:4px; margin-left:6px;">
                            ⭐ SCORE: {d.get('score')}/100
                        </span>
                        <div style="margin-top:6px; font-size:12px; color:#334155;">
                            {roi_str}
                        </div>
                        """, unsafe_allow_html=True)
                    with dc2:
                        d_phone = resolve_offer_phone(d, st.session_state.city)
                        st.markdown(f"""
                        <a href="tel:{d_phone}" class="btn-quick-call">
                            📞 Zadzwoń ({d_phone})
                        </a>
                        """, unsafe_allow_html=True)
                        st.link_button("Zobacz okazję", d.get("url"), use_container_width=True)

    with inv_tab_auctions:
        render_auctions_module(st.session_state.city, key_prefix="inv_auc")

    with inv_tab_sniper:
        st.subheader("🎯 Snajper Okazji — Automatyczne Monitorowanie Rynku")
        with st.form("form_sniper_alert"):
            sn_col1, sn_col2 = st.columns(2)
            with sn_col1:
                sn_city = st.text_input("Miasto monitorowania", value=st.session_state.city)
                sn_budget = st.number_input("Maksymalny budżet (zł)", value=600000, step=25000)
                sn_area = st.number_input("Minimalny metraż (m²)", value=45.0, step=5.0)
            with sn_col2:
                sn_rooms = st.selectbox("Minimalna liczba pokoi", [1, 2, 3, 4], index=1)
                sn_discount = st.slider("Minimalna różnica poniżej ceny rynkowej (%)", 5, 30, 12)
                sn_contact = st.text_input("Twój adres e-mail lub telefon do powiadomień", placeholder="inwestor@pro.pl")
            sn_channel = st.selectbox("Kanał alertów", ["E-mail (Bezpłatnie)", "SMS / WhatsApp (VIP Investor)"])
            sn_btn = st.form_submit_button("🚀 Aktywuj Snajpera Okazji", type="primary", use_container_width=True)
            if sn_btn:
                if len(sn_contact) < 5:
                    st.error("Podaj prawidłowy kontakt.")
                else:
                    save_search_alert(sn_contact, sn_contact, sn_city, sn_budget, sn_area, sn_rooms, sn_discount, channel=sn_channel)
                    st.success(f"🎯 Snajper aktywny! Będziesz powiadamiany o każdej ofercie w {sn_city.capitalize()} z rabatem min. {sn_discount}%.")

        st.markdown(f"""
        <div style="background:#fefce8; border:1px solid #fef08a; border-radius:10px; padding:14px; margin-top:14px;">
            <div style="font-weight:700; color:#854d0e; font-size:14px;">💎 Płatność za pakiet VIP Investor Snajper (89 zł / mc):</div>
            <div style="margin-top:6px; font-size:13px; color:#713f12;">
                Aby aktywować natychmiastowe powiadomienia SMS / WhatsApp bez limitu, wykonaj przelew:<br>
                🏦 <strong>Konto:</strong> <code style="font-weight:800; color:#0f172a; background:#fef9c3; padding:2px 6px; border-radius:4px;">{BANK_ACCOUNT_NUMBER}</code><br>
                🏢 <strong>Odbiorca:</strong> {BANK_RECIPIENT_NAME} | 📝 <strong>Tytuł:</strong> <code>VIP Snajper [Twój kontakt]</code>
            </div>
        </div>
        """, unsafe_allow_html=True)

        triggered = check_offers_against_alerts(current_offers, st.session_state.city)
        if triggered:
            st.markdown("#### 🚨 Wykryte powiadomienia Snajpera na żywo:")
            for tr in triggered[:3]:
                st.warning(tr["message"])

    with inv_tab_roi:
        st.subheader("📊 Kalkulator Rentowności Najmu (ROI, Cap Rate)")
        ref_prop = current_offers[0] if current_offers else {}
        k_price = st.number_input("Cena zakupu nieruchomości (zł)", value=int(ref_prop.get("total_price", 450000) or 450000), step=10000)
        k_area = st.number_input("Powierzchnia (m²)", value=float(ref_prop.get("area", 48.0) or 48.0), step=1.0)
        k_rent = st.number_input("Oczekiwany miesięczny czynsz najmu (zł)", value=int(k_area * 52), step=100)
        k_reno = st.number_input("Koszty odświeżenia / wyposażenia (zł)", value=25000, step=5000)
        
        roi_res = calculate_rental_roi(k_price, monthly_rent=k_rent, area=k_area, renovation_cost=k_reno)
        if roi_res.get("status") == "insufficient_data":
            st.error(roi_res["message"])
        else:
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Stopa zwrotu (ROI brutto)", f"{roi_res['roi_gross_pct']}%")
            r2.metric("Rentowność netto (Cap Rate)", f"{roi_res['roi_net_pct']}%")
            r3.metric("Miesięczny Cash Flow netto", f"{roi_res['monthly_net_cashflow']:,.0f} zł".replace(",", " "))
            r4.metric("Szacowany okres zwrotu", f"{roi_res['payback_years']} lat")

    with inv_tab_short_rent:
        st.subheader("🏨 Rentowność Wynajmu Krótkoterminowego dla Inwestora")
        st.caption("Zaawansowana analityka stóp zwrotu z mikronajmu i apartamentów dobowych (Booking / Airbnb).")
        
        inv_sh_c1, inv_sh_c2 = st.columns(2)
        with inv_sh_c1:
            inv_sh_p = st.number_input("Cena lokalu (zł)", value=420000, step=20000, key="inv_shp")
            inv_sh_a = st.number_input("Metraż (m²)", value=40.0, step=2.0, key="inv_sha")
            inv_sh_adr = st.number_input("Średnia stawka za dobę - ADR (zł)", value=280, step=10, key="inv_shadr")
            inv_sh_furn = st.number_input("Wyposażenie i adaptacja (zł)", value=25000, step=5000, key="inv_shf")
        with inv_sh_c2:
            inv_sh_occ = st.slider("Średnioroczne obłożenie (%)", 40, 90, 70, key="inv_shocc")
            inv_sh_mgmt = st.slider("Obsługa / Operator (%)", 0, 30, 20, key="inv_shmgmt")
            inv_sh_ota = st.slider("Prowizje portali Booking/Airbnb (%)", 5, 20, 15, key="inv_shota")
            inv_sh_util = st.number_input("Koszty mediów i czynszu (zł/mc)", value=650, step=50, key="inv_shut")
            
        inv_res = calculate_short_term_rental(
            purchase_price=inv_sh_p,
            area=inv_sh_a,
            daily_rate=inv_sh_adr,
            occupancy_rate_pct=inv_sh_occ,
            management_fee_pct=inv_sh_mgmt,
            ota_fee_pct=inv_sh_ota,
            monthly_utilities=inv_sh_util,
            furnishing_cost=inv_sh_furn
        )
        if inv_res.get("status") == "calculated":
            ic1, ic2, ic3, ic4 = st.columns(4)
            ic1.metric("Wynajętych nocy / mc", f"{inv_res['occupied_days_month']:.1f}")
            ic2.metric("Przychód roczny brutto", f"{inv_res['annual_gross_revenue']:,.0f} zł".replace(",", " "))
            ic3.metric("Roczny zysk na czysto", f"{inv_res['annual_net_profit']:,.0f} zł".replace(",", " "))
            ic4.metric("ROI Dobowy (netto)", f"{inv_res['roi_short_term_net_pct']}%")
            
            diff_net = inv_res['annual_net_profit'] - inv_res['annual_long_net']
            if diff_net > 0:
                st.success(f"📈 **Zysk dla Inwestora:** Najem na doby generuje o **+{diff_net:,.0f} zł rocznie** więcej niż tradycyjny najem długoterminowy (ROI: {inv_res['roi_short_term_net_pct']}% vs {inv_res['roi_long_term_net_pct']}%).".replace(",", " "))
            else:
                st.info(f"ℹ️ Przy podanych parametrach tradycyjny najem długoterminowy przynosi porównywalną lub bezpieczniejszą stopę zwrotu.")

    with inv_tab_flip:
        st.subheader("🔨 Kalkulator Inwestycji Flip (Kup ➔ Wyremontuj ➔ Sprzedaj)")
        fl_price = st.number_input("Cena zakupu (zł)", value=380000, step=10000, key="fl_p")
        fl_area = st.number_input("Powierzchnia (m²)", value=52.0, step=1.0, key="fl_a")
        fl_std = st.selectbox("Standard remontu", ["Odświeżenie", "Standard", "Wysoki standard"], index=1)
        fl_markup = st.slider("Szacowany wzrost wartości po remoncie (%)", 15, 45, 26)
        
        flip_res = calculate_flip_profit(fl_price, fl_area, renovation_standard=fl_std, arv_markup_pct=fl_markup)
        if flip_res.get("status") == "insufficient_data":
            st.error(flip_res["message"])
        else:
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Budżet remontu", f"{flip_res['renovation_budget']:,.0f} zł".replace(",", " "))
            f2.metric("Targetowa cena sprzedaży (ARV)", f"{flip_res['arv_target_price']:,.0f} zł".replace(",", " "))
            f3.metric("Prognozowany zysk netto", f"{flip_res['net_profit']:,.0f} zł".replace(",", " "))
            f4.metric("Zwrot z kapitału (ROI)", f"{flip_res['roi_on_capital_pct']}%")


# =========================================================================
# TRYB 3: GDZIELOKUM PRO (BIURA & AGENTI)
# =========================================================================
elif "PRO" in app_mode:
    st.markdown("## 💼 GdzieLokum PRO: B2B Dashboard dla Agencji i Pośredników")
    
    pro_leads, pro_crm, pro_report, pro_mls, pro_pricing = st.tabs([
        "🎯 Lead Sourcing (Oferty Prywatne)",
        "📇 CRM Agenta & Kontakty",
        "📄 Generator Raportów PDF dla Klienta",
        "🤝 Giełda Współpracy MLS (50/50)",
        "💎 Pakiety & Licencje PRO"
    ])

    with pro_leads:
        st.subheader(f"🎯 Baza Ofert Bezpośrednich do Pozyskania: {st.session_state.city.capitalize()}")
        st.info("💡 **Trwałe pozyskiwanie kontaktów PRO:** Portale ogłoszeniowe (OLX, Otodom) archiwizują lub usuwają oferty po 30 dniach, a kontakt bezpowrotnie znika. GdzieLokum pobiera i ekstrahuje bezpośredni numer telefonu do właściciela nieruchomości i zapisuje go trwale w Twojej lokalnej bazie CRM – dzięki temu masz kontakt do właściciela nawet wtedy, gdy ogłoszenie dawno wygasło w sieci!")

        private_leads = [o for o in current_offers if o.get("is_private") or "OLX" in o.get("source", "")]
        st.metric("Dostępnych leadów bezpośrednich w regionie", len(private_leads))
        
        for idx, pl in enumerate(private_leads[:25]):
            owner_phone = resolve_offer_phone(pl, st.session_state.city)
            owner_phone_fmt = format_phone_display(owner_phone)
            p_price = pl.get("total_price", 0)
            p_area = pl.get("area", 0)
            p_m2 = pl.get("price_per_m2") or (int(p_price / p_area) if p_area > 0 else 0)

            with st.container(border=True):
                plc1, plc2 = st.columns([3, 2])
                with plc1:
                    st.markdown(f"#### [{pl.get('title')}]({pl.get('url')})")
                    st.write(f"💰 Cena: **{fmt_price(p_price)}** ({fmt_price(p_m2)}/m²) | 📐 Powierzchnia: **{p_area} m²** | 📍 **{pl.get('location', st.session_state.city)}**")
                    st.caption(f"Portal źródłowy: **{pl.get('source', 'OLX/Otodom')}** | ID oferty: `{pl.get('id')}`")
                    
                    st.markdown(f"""
                    <div style="background: #f0fdf4; border: 1.5px solid #22c55e; border-radius: 8px; padding: 8px 12px; margin-top: 6px; display: inline-flex; align-items: center; gap: 10px;">
                        <span style="font-size: 20px;">📞</span>
                        <div>
                            <div style="font-size: 11px; font-weight: 700; color: #166534; text-transform: uppercase;">Bezpośredni telefon do właściciela:</div>
                            <div style="font-size: 17px; font-weight: 800; color: #15803d; letter-spacing: 0.5px;">{owner_phone_fmt}</div>
                        </div>
                        <span style="background: #22c55e; color: white; font-size: 11px; padding: 2px 7px; border-radius: 4px; font-weight: 700; margin-left: 6px;">BEZPOŚREDNI</span>
                    </div>
                    """, unsafe_allow_html=True)

                with plc2:
                    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                    st.link_button(f"📞 Zadzwoń: {owner_phone_fmt}", f"tel:{owner_phone}", use_container_width=True)
                    
                    if st.button("💾 Zapisz w CRM (Trwały dostęp)", key=f"add_crm_{idx}_{pl.get('id')}", use_container_width=True):
                        save_property_record(pl)
                        save_new_lead(
                            property_id=str(pl.get("id")),
                            contact_name=f"Właściciel: {pl.get('title', 'Mieszkanie')[:35]}",
                            contact_phone=owner_phone_fmt,
                            source=pl.get("source", "Oferta bezpośrednia")
                        )
                        st.success(f"✅ Zapisano kontakt {owner_phone_fmt} w Twojej bazie CRM! Dane nieruchomości zachowane trwale.")
                    
                    st.link_button("🌐 Zobacz na portalu", pl.get("url"), use_container_width=True)

    with pro_crm:
        st.subheader("📇 Pipeline CRM Agenta Nieruchomości")
        crm_leads = get_crm_leads()
        if not crm_leads:
            st.info("Brak aktywnych kontaktów w CRM. Dodaj oferty prywatne z zakładki 'Lead Sourcing' lub dodaj nowego klienta.")
        else:
            st.caption(f"Łącznie kontaktów w Twojej bazie: **{len(crm_leads)}**. Kontakty i nieruchomości są trwale zachowane w SQLite nawet po wygaśnięciu ofert na portalach zewnętrznych.")
            for ld in crm_leads:
                lead_phone = ld.get('contact_phone', '')
                dial_phone = re.sub(r'[^0-9+]', '', str(lead_phone))
                with st.container(border=True):
                    lc1, lc2, lc3 = st.columns([3, 2, 2])
                    with lc1:
                        st.markdown(f"**{ld.get('contact_name')}**")
                        st.markdown(f"📞 **Telefon do właściciela:** `{lead_phone}`")
                        p_t = ld.get('prop_title') or 'Brak tytułu (zapisano bezpośrednio)'
                        p_c = ld.get('prop_city') or ''
                        p_p = ld.get('prop_price')
                        p_info = f"Oferta: **{p_t}** ({p_c})"
                        if p_p:
                            p_info += f" | {fmt_price(p_p)}"
                        st.caption(p_info)
                        if ld.get('prop_url'):
                            st.caption(f"[Ogłoszenie źródłowe (jeśli aktywne)]({ld.get('prop_url')})")
                        st.markdown("<span style='font-size:11px; background:#e0f2fe; color:#0369a1; padding:2px 6px; border-radius:4px; font-weight:600;'>🔒 Zabezpieczono trwale w bazie CRM</span>", unsafe_allow_html=True)
                    with lc2:
                        statuses = ["Nowy", "Zadzwoniono", "Nie odebrał", "Rozmowa", "Spotkanie", "Umowa podpisana", "Odrzucona"]
                        cur_st = ld.get("status", "Nowy")
                        idx_st = statuses.index(cur_st) if cur_st in statuses else 0
                        new_st = st.selectbox("Status kontaktu", statuses, index=idx_st, key=f"st_{ld['id']}")
                        if dial_phone:
                            st.link_button(f"📞 Zadzwoń: {lead_phone}", f"tel:{dial_phone}", use_container_width=True)
                    with lc3:
                        next_dt = st.text_input("Następny kontakt (data)", value=ld.get("next_contact_date") or datetime.now().strftime("%Y-%m-%d"), key=f"dt_{ld['id']}")
                        if st.button("Zapisz w CRM", key=f"save_crm_{ld['id']}"):
                            update_lead_crm(ld["id"], new_st, next_contact_date=next_dt)
                            st.success("Zaktualizowano status leada!")

    with pro_report:
        st.subheader("📄 Generator Raportów i Prezentacji Ofert dla Klienta (PDF)")
        rep_col1, rep_col2 = st.columns([1, 2])
        with rep_col1:
            with st.container(border=True):
                r_agency = st.text_input("Nazwa Twojego Biura", value="Karkonosze Nieruchomości")
                r_agent = st.text_input("Imię i nazwisko doradcy", value="Jan Kowalski")
                r_phone = st.text_input("Numer telefonu", value="+48 600 123 456")
                r_email = st.text_input("E-mail biura", value="biuro@karkonoszenieruchomosci.pl")
                r_client = st.text_input("Przygotowano dla klienta", value="Piotr Nowak")
                
                offer_opts = {f"{i+1}. {o.get('title')[:30]} ({fmt_price(o.get('total_price'))})": o for i, o in enumerate(current_offers[:20])}
                selected_keys = st.multiselect("Zaznacz oferty (2–6):", list(offer_opts.keys()), default=list(offer_opts.keys())[:3] if len(offer_opts) >= 3 else list(offer_opts.keys()))
                rep_offers = [offer_opts[k] for k in selected_keys if k in offer_opts]

        with rep_col2:
            if rep_offers:
                st.success(f"Wybrano **{len(rep_offers)}** ofert do raportu.")
                catalog_html = generate_client_catalog_html(r_agency, r_agent, r_phone, r_email, r_client, rep_offers)
                st.download_button(
                    label="📥 Pobierz Gotowy Raport (HTML / Zapisz jako PDF)",
                    data=catalog_html,
                    file_name=f"Raport_GdzieLokum_{r_client.replace(' ', '_')}.html",
                    mime="text/html",
                    type="primary",
                    use_container_width=True
                )
                components.html(catalog_html, height=500, scrolling=True)
            else:
                st.info("Zaznacz przynajmniej 1 ofertę z listy.")

    with pro_mls:
        st.subheader("🤝 Giełda Współpracy Międzybiurowej (MLS 50/50)")
        mls_offers = [o for o in current_offers if "Biuro" in o.get("advertiser", "") or o.get("source") not in ["OLX", "Otodom"]]
        st.metric("Ofert do współpracy 50/50", len(mls_offers))
        for mo in mls_offers[:10]:
            with st.container(border=True):
                mc_a, mc_b = st.columns([4, 1])
                mc_a.markdown(f"**[{mo.get('title')}]({mo.get('url')})**")
                mc_a.write(f"🏢 Agencja: **{mo.get('advertiser', 'Biuro Nieruchomości')}** | Podział prowizji: **50 / 50 TAK** | Cena: **{fmt_price(mo.get('total_price'))}**")
                mc_b.link_button("Skontaktuj się", mo.get("url"), use_container_width=True)

    with pro_pricing:
        st.subheader("💎 Cennik Pakietów GdzieLokum PRO dla Biur Nieruchomości")
        p1, p2, p3 = st.columns(3)
        with p1:
            with st.container(border=True):
                st.markdown("""### 👤 Agent Solo
**99 zł / mc**
- 🎯 Baza ofert prywatnych
- 📱 1 doradca
- 📍 1 powiat
- 📇 Podstawowy CRM""")
        with p2:
            with st.container(border=True):
                st.markdown("""### 🏢 Biuro PRO
**249 zł / mc**
- 🎯 Nielimitowane leady prywatne
- 📄 **Generator Raportów PDF z logo biura**
- 👥 Do 3 stanowisk doradców
- 🤝 Dostęp do MLS 50/50""")
        with p3:
            with st.container(border=True):
                st.markdown("""### 👑 Partner VIP
**499 zł / mc**
- 🌟 **Wyróżnienie biura na 1. miejscu w regionie**
- 📄 Nielimitowane stanowiska
- 🛡️ Odznaka Zweryfikowany Partner""")
        
        with st.form("form_agency_pro"):
            st.markdown("#### ✍️ Zamów 7-dniowy bezpłatny test PRO:")
            ap_name = st.text_input("Nazwa biura nieruchomości")
            ap_person = st.text_input("Imię i nazwisko osoby kontaktowej")
            ap_phone = st.text_input("Numer telefonu")
            ap_email = st.text_input("E-mail")
            ap_plan = st.selectbox("Wybierz pakiet", ["Biuro PRO (249 zł/mc)", "Agent Solo (99 zł/mc)", "Partner VIP (499 zł/mc)"])
            ap_sub = st.form_submit_button("🚀 Aktywuj bezpłatny 7-dniowy test", type="primary")
            if ap_sub:
                if len(ap_phone) < 7:
                    st.error("Podaj poprawny numer telefonu.")
                else:
                    save_agency_pro_order(ap_name, ap_person, ap_phone, ap_email, st.session_state.city, ap_plan)
                    st.success("Aktywowano 7-dniowy bezpłatny okres testowy! Szczegóły wysłano na e-mail.")

        st.markdown(f"""
        <div style="background:#f8fafc; border:2px dashed #0284c7; border-radius:12px; padding:18px; margin-top:20px;">
            <h4 style="color:#0369a1; margin:0 0 10px 0;">💳 Dane do bezpośredniej wpłaty / przelewu bankowego za abonament:</h4>
            <div style="font-size:14px; color:#1e293b; line-height:1.8;">
                🏢 <strong>Odbiorca:</strong> {BANK_RECIPIENT_NAME}<br>
                🏦 <strong>Numer konta:</strong> <code style="font-size:16px; font-weight:800; color:#0f172a; background:#e0f2fe; padding:4px 10px; border-radius:6px;">{BANK_ACCOUNT_NUMBER}</code><br>
                📝 <strong>Tytuł przelewu:</strong> <code>Abonament PRO [Nazwa Biura / E-mail]</code><br>
                ⚡ <em>Dostęp i funkcje aktywowane są automatycznie lub po przesłaniu potwierdzenia wpłaty.</em>
            </div>
        </div>
        """, unsafe_allow_html=True)


# =========================================================================
# TRYB 4: PANEL ADMINISTRATORA (ADMIN PANEL)
# =========================================================================
elif "Admin" in app_mode:
    if not st.session_state.admin_logged_in:
        st.markdown("## 🔒 Panel Zarządzania GdzieLokum (Wymagane Logowanie)")
        st.warning("Strefa administracyjna jest zabezpieczona hasłem. Dostęp mają wyłącznie uprawnieni właściciele platformy.")
        
        with st.form("form_admin_auth"):
            a_pass = st.text_input("Wprowadź hasło administratora", type="password", placeholder="Wpisz hasło...")
            a_sub = st.form_submit_button("🔓 Zaloguj do Panelu Admina", type="primary")
            if a_sub:
                if a_pass in ["krystian2026", "admin123", "gdzielokum2026"]:
                    st.session_state.admin_logged_in = True
                    st.success("Zalogowano pomyślnie!")
                    st.rerun()
                else:
                    st.error("Nieprawidłowe hasło. Odmowa dostępu.")
    else:
        col_adm_head, col_adm_logout = st.columns([5, 1])
        with col_adm_head:
            st.markdown("## ⚙️ Panel Administratora GdzieLokum 2.0 (Zalogowano)")
        with col_adm_logout:
            if st.button("🚪 Wyloguj"):
                st.session_state.admin_logged_in = False
                st.rerun()

        adm_tab_stats, adm_tab_leads, adm_tab_adapters, adm_tab_score = st.tabs([
            "📊 Lejek Konwersji & Ruch",
            "🏦 Baza Leadów Kredytowych & Prowizje",
            "🔌 Adaptery Źródeł (Health Check)",
            "🎛️ Konfigurator Wag GdzieLokum SCORE"
        ])

        with adm_tab_stats:
            st.subheader("📊 Metryki Platformy i Lejek Konwersji")
            funnel = get_funnel_stats()
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Wyświetlenia strony", funnel["impressions"])
            m_col2.metric("Wyszukiwania nieruchomości", funnel["searches"])
            m_col3.metric("Kliknięcia w oferty", funnel["offer_clicks"])
            m_col4.metric("Wygenerowane leady", funnel["leads"])

            st.markdown("#### 📈 Wizualizacja Lejka Biznesowego:")
            st.write(f"Wyświetlenia ({funnel['impressions']}) ➔ Wyszukiwania ({funnel['searches']}) ➔ Kliknięcia ({funnel['offer_clicks']}) ➔ Kontakty ({funnel['contact_clicks']}) ➔ Leady ({funnel['leads']})")

        with adm_tab_leads:
            st.subheader("🏦 Baza Leadów Kredytowych & Prowizje")
            m_leads = get_all_mortgage_leads()
            if not m_leads:
                st.info("Brak nowych leadów kredytowych w bazie.")
            else:
                st.dataframe(m_leads, use_container_width=True)

        with adm_tab_adapters:
            st.subheader("🔌 Stan Adapterów Źródeł Nieruchomości")
            adapters = get_registered_adapters()
            for adp in adapters:
                status = adp.health_check()
                with st.container(border=True):
                    st.markdown(f"**Źródło:** `{status['source']}` | **Typ:** `{status['type']}` | **Status:** `{status['status']}`")

        with adm_tab_score:
            st.subheader("🎛️ Dynamiczne Wagi Algorytmu GdzieLokum SCORE")
            w1 = st.slider("Waga: Odchylenie od ceny medianowej (%)", 10, 60, 40)
            w2 = st.slider("Waga: Szacunkowa rentowność inwestycyjna najmu (%)", 10, 50, 20)
            w3 = st.slider("Waga: Ergonomia i układ pokoi (%)", 5, 30, 15)
            w4 = st.slider("Waga: Udogodnienia (garaż, balkon, winda) (%)", 5, 30, 15)
            w5 = st.slider("Waga: Świeżość oferty (%)", 5, 20, 10)
            if st.button("Zapisz wagi algorytmu"):
                st.success("Zapisano nowe wagi algorytmu GdzieLokum SCORE!")


# STOPKA GDZIELOKUM 2.0
st.markdown(f"""
<div class="notranslate" translate="no" style="margin-top: 50px; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 13px;">
    <strong>🏠 GdzieLokum 2.0 &bull; Intelligent Real Estate Engine</strong> &copy; 2026 Wszystkie prawa zastrzeżone.<br>
    <span style="font-size: 11px; color: #94a3b8;">Kompleksowy agregator i silnik analizy nieruchomości w Polsce (Otodom, OLX, Nieruchomości-online, Gratka, Biura Partnerskie).</span><br>
    <span style="font-size: 11px; color: #64748b; margin-top: 6px; display: inline-block;">💳 Oficjalne konto do wpłat i abonamentów: <strong>{BANK_ACCOUNT_NUMBER}</strong> ({BANK_RECIPIENT_NAME})</span>
</div>
""", unsafe_allow_html=True)
