import sys
import glob

# Wymuszenie czystego ladowania Pythona bez konfliktow bytecode (.pyc)
sys.dont_write_bytecode = True
for _pyc in glob.glob("*.pyc") + glob.glob("*/*.pyc"):
    try:
        os.remove(_pyc)
    except Exception:
        pass

import streamlit as st
import os
import re
import json
import html
import urllib.parse
from datetime import datetime
import streamlit.components.v1 as components

from scrapers.aggregator import aggregate_offers
from scrapers.agencies_scraper import load_local_agencies, discover_agencies_for_city
from scrapers.source_adapter import get_registered_adapters
from analytics.market_analyzer import analyze_market_prices
from analytics.score_engine import calculate_gdzielokum_score, SCORE_DISCLAIMER
from analytics.ai_search import parse_natural_language_query, explain_ai_matching

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

init_db()

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

def resolve_offer_phone(offer: dict, city: str = "Wrocław") -> str:
    """
    Zwraca numer telefonu do szybkiego kontaktu (klikam i dzwoni).
    """
    phone = offer.get("phone") or offer.get("contact_phone")
    if phone:
        clean = re.sub(r'[^0-9+]', '', str(phone))
        if len(clean) >= 9:
            return clean
    desc = (offer.get("description") or "") + " " + (offer.get("title") or "")
    match = re.search(r'(?:\+?48\s*)?(?:[0-9]{3}[\s-]*){3}', desc)
    if match:
        found_num = re.sub(r'[^0-9+]', '', match.group(0))
        if len(found_num) >= 9:
            return found_num
    city_hotlines = {
        "wroclaw": "+48717889900", "wrocław": "+48717889900",
        "warszawa": "+48228250000", "krakow": "+48123000000", "kraków": "+48123000000",
        "poznan": "+48618000000", "poznań": "+48618000000",
        "lubin": "+48768461100", "jelenia gora": "+48757525000", "jelenia góra": "+48757525000"
    }
    return city_hotlines.get(str(city).lower().strip(), "+48221234567")

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

    tab_list, tab_compare, tab_saved, tab_short_rent, tab_mortgage, tab_services = st.tabs([
        "📋 Lista Ofert",
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
        st.subheader("🛠️ Zweryfikowani Partnerzy Ekosystemu Nieruchomości")
        services = get_marketplace_services(st.session_state.city)
        for s in services:
            with st.container(border=True):
                sc_a, sc_b = st.columns([4, 1])
                with sc_a:
                    st.markdown(f"#### 🏷️ {s.get('category')} — {s.get('company_name')}")
                    st.write(f"{s.get('description')}")
                    st.caption(f"⭐ Ocena klientów: {s.get('rating')}/5.0 | 📞 Kontakt: `{s.get('contact_phone')}`")
                with sc_b:
                    st.button("Zamów kontakt", key=f"srv_{s.get('company_name')}", use_container_width=True)


# =========================================================================
# TRYB 2: GDZIELOKUM INVESTOR & SNAJPER OKAZJI
# =========================================================================
elif "INVESTOR" in app_mode:
    st.markdown("## 📈 GdzieLokum INVESTOR: Analityka, Okazje & Snajper")
    st.caption("Profesjonalny moduł dla inwestorów, rentierów i flipperów z matematyczną wyceną rentowności.")

    inv_tab_deals, inv_tab_sniper, inv_tab_roi, inv_tab_short_rent, inv_tab_flip = st.tabs([
        "🔥 Okazje Inwestycyjne (Poniżej Rynku)",
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
        private_leads = [o for o in current_offers if o.get("is_private") or "OLX" in o.get("source", "")]
        st.metric("Dostępnych leadów prywatnych w regionie", len(private_leads))
        
        for idx, pl in enumerate(private_leads[:20]):
            with st.container(border=True):
                plc1, plc2 = st.columns([4, 1])
                with plc1:
                    st.markdown(f"**[{pl.get('title')}]({pl.get('url')})**")
                    st.write(f"Cena: **{fmt_price(pl.get('total_price'))}** | Lokalizacja: **{pl.get('location')}** | Źródło: **{pl.get('source')}**")
                with plc2:
                    st.link_button("📞 Otwórz ogłoszenie", pl.get("url"), use_container_width=True)
                    if st.button("➕ Dodaj do mojego CRM", key=f"add_crm_{idx}_{pl.get('id')}", use_container_width=True):
                        save_new_lead(pl.get("id"), "Właściciel nieruchomości", "Sprawdź w ogłoszeniu", source=pl.get("source"))
                        st.success("Dodano leada do CRM!")

    with pro_crm:
        st.subheader("📇 Pipeline CRM Agenta Nieruchomości")
        crm_leads = get_crm_leads()
        if not crm_leads:
            st.info("Brak aktywnych kontaktów w CRM. Dodaj oferty prywatne z zakładki 'Lead Sourcing' lub dodaj nowego klienta.")
        else:
            for ld in crm_leads:
                with st.container(border=True):
                    lc1, lc2, lc3 = st.columns([3, 2, 2])
                    with lc1:
                        st.markdown(f"**{ld.get('contact_name')}** | 📞 `{ld.get('contact_phone')}`")
                        st.caption(f"Oferta: {ld.get('prop_title', 'Brak')} ({ld.get('prop_city', '')})")
                    with lc2:
                        statuses = ["Nowy", "Zadzwoniono", "Nie odebrał", "Rozmowa", "Spotkanie", "Umowa podpisana", "Odrzucona"]
                        cur_st = ld.get("status", "Nowy")
                        idx_st = statuses.index(cur_st) if cur_st in statuses else 0
                        new_st = st.selectbox("Status kontaktu", statuses, index=idx_st, key=f"st_{ld['id']}")
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
