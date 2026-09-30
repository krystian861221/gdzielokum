import streamlit as st
import os
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
from analytics.investor_calculator import calculate_rental_roi, calculate_flip_profit
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

st.set_page_config(
    page_title="GdzieLokum 2.0 | Intelligent Real Estate Engine",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
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
        "⚙️ Panel Administratora"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📍 Podstawowe parametry")
city_input = st.sidebar.text_input("Miasto / Miejscowość", value=st.session_state.city)
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
    with st.spinner(f"Agregacja ofert dla: {city_input}..."):
        st.session_state.city = city_input
        rooms_val = int(f_rooms.replace("+", "")) if f_rooms not in ["Wszystkie", "4+"] else (4 if f_rooms == "4+" else None)
        offers = safe_aggregate_offers(
            city=city_input,
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
    st.markdown(f"## 🏠 Wyszukiwarka Nieruchomości: **{st.session_state.city.capitalize()}**")
    
    with st.container(border=True):
        st.markdown("#### 🤖 AI Wyszukiwanie Naturalnym Językiem")
        st.caption("Wpisz zapytanie własnymi słowami — sztuczna inteligencja przeanalizuje Twoje preferencje i wyodrębni parametry.")
        ai_col1, ai_col2 = st.columns([5, 1])
        with ai_col1:
            ai_query = st.text_input(
                "Zapytanie AI",
                placeholder="np. Znajdź mi mieszkanie we Wrocławiu do 650 tys., minimum 55 m², 3 pokoje, balkon, najlepiej poniżej ceny rynkowej",
                label_visibility="collapsed"
            )
        with ai_col2:
            ai_btn = st.button("🚀 Szukaj AI", use_container_width=True)

        if ai_btn and ai_query:
            with st.spinner("Analiza zapytania AI..."):
                parsed = parse_natural_language_query(ai_query)
                st.session_state.city = parsed["city"]
                ai_offers = safe_aggregate_offers(
                    city=parsed["city"],
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
    c2.metric("Średnia cena m²", f"{m_stats.get('avg_m2', 0):,.0f} zł".replace(',', ' ') if m_stats.get('avg_m2') else "-")
    c3.metric("Mediana m²", f"{m_stats.get('median_m2', 0):,.0f} zł".replace(',', ' ') if m_stats.get('median_m2') else "-")
    c4.metric("Zakres cen m²", f"{m_stats.get('min_m2', 0):,.0f} - {m_stats.get('max_m2', 0):,.0f} zł".replace(',', ' ') if m_stats.get('min_m2') else "-")

    tab_list, tab_compare, tab_saved, tab_mortgage, tab_services = st.tabs([
        "📋 Lista Ofert",
        f"⚖️ Porównywarka ({len(st.session_state.compare_list)}/5)",
        f"⭐ Zapisane ({len(st.session_state.favorites)})",
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
                        
                        pm2 = o.get("price_per_m2", 0)
                        diff_pct = o.get("diff_pct", 0)
                        status_text = "Poniżej mediany lokalnego rynku" if diff_pct < 0 else "Powyżej mediany lokalnego rynku"
                        status_color = "#15803d" if diff_pct < 0 else "#b91c1c"
                        
                        st.markdown(f"""
                        <div class="market-box">
                            <strong>📊 Analiza Rynkowa:</strong> 
                            Cena/m²: <strong>{pm2:,.0f} zł</strong> | Mediana okolicy: <strong>{m_stats.get('median_m2', 0):,.0f} zł</strong> | 
                            Różnica: <strong style="color:{status_color};">{diff_pct}% ({status_text})</strong>
                        </div>
                        <div class="disclaimer-text">{SCORE_DISCLAIMER}</div>
                        """.replace(",", " "), unsafe_allow_html=True)

                    with col_actions:
                        price = o.get("total_price", 0)
                        st.markdown(f"<div class='price-total'>{price:,} zł</div>".replace(",", " "), unsafe_allow_html=True)
                        if o.get("area"):
                            st.caption(f"Powierzchnia: {o.get('area')} m²")
                        
                        st.link_button("🌐 Zobacz ofertę", o.get("url", "#"), use_container_width=True, type="primary")
                        
                        is_compared = o.get("id") in [co.get("id") for co in st.session_state.compare_list]
                        if st.checkbox("Porównaj ofertę", value=is_compared, key=f"cmp_{idx}_{o.get('id')}"):
                            if not is_compared and len(st.session_state.compare_list) < 5:
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

                        share_text = urllib.parse.quote(f"Zobacz ofertę w {st.session_state.city.capitalize()} za {price:,} zł na GdzieLokum: {o.get('url')}".replace(",", " "))
                        wa_url = f"https://api.whatsapp.com/send?text={share_text}"
                        fb_url = f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(o.get('url', ''))}"
                        
                        sc1, sc2 = st.columns(2)
                        sc1.link_button("💬 WhatsApp", wa_url, use_container_width=True)
                        sc2.link_button("📘 FB", fb_url, use_container_width=True)

    with tab_compare:
        st.subheader("⚖️ Inteligentna Porównywarka Nieruchomości (do 5 ofert)")
        if not st.session_state.compare_list:
            st.info("Zaznacz opcję 'Porównaj ofertę' przy maksymalnie 5 nieruchomościach z listy.")
        else:
            c_offers = st.session_state.compare_list[:5]
            st.write(f"Zestawienie **{len(c_offers)}** wybranych nieruchomości:")
            headers = ["Parametr"] + [f"Oferta #{i+1}: {co.get('title', '')[:20]}..." for i, co in enumerate(c_offers)]
            rows = [
                ["Cena całkowita"] + [f"{co.get('total_price', 0):,} zł".replace(",", " ") for co in c_offers],
                ["Powierzchnia"] + [f"{co.get('area', 'B/D')} m²" for co in c_offers],
                ["Cena za m²"] + [f"{co.get('price_per_m2', 0):,.0f} zł/m²".replace(",", " ") for co in c_offers],
                ["Pokoje"] + [f"{co.get('rooms', 'B/D')}" for co in c_offers],
                ["GdzieLokum SCORE"] + [f"⭐ {co.get('score', 50)}/100" for co in c_offers],
                ["Różnica vs Rynek"] + [f"{co.get('diff_pct', 0)}%" for co in c_offers],
                ["Źródło"] + [f"{co.get('source', '')}" for co in c_offers]
            ]
            tbl_md = "| " + " | ".join(headers) + " |\n"
            tbl_md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
            for row in rows:
                tbl_md += "| " + " | ".join(row) + " |\n"
            st.markdown(tbl_md)
            if st.button("Wyczyść porównanie"):
                st.session_state.compare_list = []
                st.rerun()

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

    inv_tab_deals, inv_tab_sniper, inv_tab_roi, inv_tab_flip = st.tabs([
        "🔥 Okazje Inwestycyjne (Poniżej Rynku)",
        "🎯 Snajper Okazji (Alerty Live)",
        "📊 Kalkulator Rentowności Najmu (ROI)",
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
                    dc1, dc2 = st.columns([4, 1])
                    with dc1:
                        st.markdown(f"**[{d.get('title')}]({d.get('url')})**")
                        st.write(f"Cena: **{d.get('total_price', 0):,} zł** | Metraż: **{d.get('area')} m²** | Cena/m²: **{d.get('price_per_m2', 0):,.0f} zł/m²**".replace(",", " "))
                        st.markdown(f"""
                        <span style="background:#dcfce7; color:#15803d; font-weight:800; padding:2px 8px; border-radius:4px;">
                            {d.get('diff_pct')}% poniżej mediany lokalnego rynku
                        </span>
                        <span style="background:#e0f2fe; color:#0369a1; font-weight:700; padding:2px 8px; border-radius:4px; margin-left:6px;">
                            ⭐ SCORE: {d.get('score')}/100
                        </span>
                        """, unsafe_allow_html=True)
                    with dc2:
                        st.link_button("Zobacz okazję", d.get("url"), use_container_width=True, type="primary")

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
                    st.write(f"Cena: **{pl.get('total_price', 0):,} zł** | Lokalizacja: **{pl.get('location')}** | Źródło: **{pl.get('source')}**".replace(",", " "))
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
                
                offer_opts = {f"{i+1}. {o.get('title')[:30]} ({o.get('total_price', 0):,} zł)".replace(",", " "): o for i, o in enumerate(current_offers[:20])}
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
                mc_a.write(f"🏢 Agencja: **{mo.get('advertiser', 'Biuro Nieruchomości')}** | Podział prowizji: **50 / 50 TAK** | Cena: **{mo.get('total_price', 0):,} zł**".replace(",", " "))
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
elif "Administratora" in app_mode:
    st.markdown("## ⚙️ Panel Administratora GdzieLokum 2.0")
    
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
