import streamlit as st
import os
import json
import html
import streamlit.components.v1 as components
from scrapers.aggregator import aggregate_offers
from scrapers.agencies_scraper import load_local_agencies, save_custom_agency, discover_agencies_for_city
from analytics.market_analyzer import analyze_market_prices
from analytics.crm_manager import get_lead_status, save_crm_status, load_crm_data
from reports.client_report import generate_client_catalog_html

# Konfiguracja strony Streamlit
st.set_page_config(
    page_title="GdzieLokum PRO | Wszystkie Nieruchomości",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .offer-card {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 16px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-otodom { background-color: #e0f2fe; color: #0369a1; }
    .badge-olx { background-color: #ccfbf1; color: #0f766e; }
    .badge-no { background-color: #dcfce7; color: #15803d; }
    .badge-agency { background-color: #ffedd5; color: #c2410c; }
    .badge-pro { background-color: #fef08a; color: #854d0e; font-weight: 700; }
    
    .deal-good { background-color: #dcfce7; color: #15803d; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
    .deal-mid { background-color: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; font-size: 11px; }
    .deal-high { background-color: #fee2e2; color: #b91c1c; padding: 3px 8px; border-radius: 4px; font-size: 11px; }

    .price-total {
        font-size: 20px;
        font-weight: 700;
        color: #16a34a;
    }
    .price-breakdown {
        font-size: 13px;
        color: #64748b;
    }
    .loc-tag {
        font-size: 13px;
        color: #475569;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Inicjalizacja stanu sesji
if "favorites" not in st.session_state:
    st.session_state.favorites = []
if "offers" not in st.session_state:
    st.session_state.offers = []
if "searched" not in st.session_state:
    st.session_state.searched = False
if "selected_for_report" not in st.session_state:
    st.session_state.selected_for_report = []

# PANEL BOCZNY
st.sidebar.markdown("""
<div class="notranslate" translate="no" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 18px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #334155; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);">
    <div style="font-size: 24px; font-weight: 900; color: #ffffff; letter-spacing: -0.5px;">
        🏠 Gdzie<span style="color: #38bdf8;">Lokum</span>
    </div>
    <div style="font-size: 11px; color: #94a3b8; margin-top: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">
        Agregator Nieruchomości
    </div>
    <div style="margin-top: 10px; display: flex; justify-content: center; gap: 6px;">
        <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">v2.0 PRO</span>
        <span style="background: rgba(34, 197, 94, 0.2); color: #4ade80; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">POLSKA LIVE</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### ⚙️ Tryb pracy")
app_mode = st.sidebar.radio(
    "Wybierz profil:",
    ["👤 Poszukujący (Standard)", "💼 GdzieLokum PRO (Dla Agencji & Pośredników)"],
    index=0
)
is_pro = "PRO" in app_mode

st.sidebar.markdown("---")
st.sidebar.header("🔍 Kryteria wyszukiwania")

city = st.sidebar.text_input("Miasto / Miejscowość", value="Jelenia Góra")
category = st.sidebar.selectbox("Rodzaj transakcji", ["Wynajem", "Kupno / Sprzedaż"], index=0)
cat_key = "wynajem" if category == "Wynajem" else "sprzedaz"

property_type = st.sidebar.selectbox(
    "Typ nieruchomości",
    ["Mieszkania", "Domy", "Działki budowlane i grunty", "Lokale użytkowe", "Pokoje"],
    index=0
)

prop_map = {
    "Mieszkania": "mieszkania",
    "Domy": "domy",
    "Działki budowlane i grunty": "dzialki",
    "Lokale użytkowe": "lokale",
    "Pokoje": "pokoje"
}
prop_key = prop_map.get(property_type, "mieszkania")

if cat_key == "wynajem":
    max_total_price = st.sidebar.slider(
        "Maksymalny budżet miesięczny (PLN)",
        min_value=500, max_value=12000, value=2400, step=50
    )
else:
    max_total_price = st.sidebar.slider(
        "Maksymalna cena zakupu (PLN)",
        min_value=50000, max_value=3000000, value=600000, step=25000
    )

sources = st.sidebar.multiselect(
    "Przeszukiwane źródła",
    ["Otodom", "OLX", "Nieruchomości-online", "Gratka / Biura"],
    default=["Otodom", "OLX", "Nieruchomości-online", "Gratka / Biura"]
)

private_only = st.sidebar.checkbox("Tylko bezpośrednio od właściciela (bez pośredników)", value=False)
sort_option = st.sidebar.selectbox("Sortowanie", ["Cena: od najniższej", "Cena: od najwyższej"])

search_btn = st.sidebar.button("🚀 Szukaj ofert", type="primary", use_container_width=True)

# AKCJA WYSZUKIWANIA
if search_btn or not st.session_state.searched:
    with st.spinner(f"Przeszukuję portale dla: {property_type} ({category}) w {city}..."):
        ads = aggregate_offers(
            city=city,
            max_total_price=max_total_price,
            category=cat_key,
            property_type=prop_key,
            sources=sources,
            private_only=private_only,
            sort_by=sort_option
        )
        st.session_state.offers = ads
        st.session_state.searched = True

offers = st.session_state.offers
# Analiza cenowa rynku
market_stats = analyze_market_prices(offers)

# NAGŁÓWEK GŁÓWNY GDZIELOKUM
if is_pro:
    hero_html = (
        f'<div class="notranslate" translate="no" style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); padding: 22px 28px; border-radius: 14px; margin-bottom: 24px; color: white; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); border: 1px solid #312e81;">'
        f'<div>'
        f'<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">'
        f'<span style="font-size: 30px; font-weight: 900; letter-spacing: -0.5px;">🏠 Gdzie<span style="color: #38bdf8;">Lokum</span></span>'
        f'<span style="background: #fef08a; color: #854d0e; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 6px;">💼 PRO DLA AGENCJI</span>'
        f'</div>'
        f'<div style="font-size: 14px; color: #cbd5e1;">Zintegrowane narzędzie B2B: Leady prywatne &bull; CRM &bull; Analiza wycen &bull; Raporty PDF &bull; Giełda MLS</div>'
        f'</div>'
        f'<div style="text-align: right; font-size: 13px; color: #94a3b8;">'
        f'<div>🔎 <strong>Otodom &bull; OLX &bull; Nieruchomości-online &bull; Gratka</strong></div>'
        f'<div style="margin-top: 4px; color: #38bdf8;">📍 <strong>{html.escape(city)}</strong> ({html.escape(property_type)} &bull; {html.escape(category)})</div>'
        f'</div>'
        f'</div>'
    )
else:
    hero_html = (
        f'<div class="notranslate" translate="no" style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 22px 28px; border-radius: 14px; margin-bottom: 24px; color: white; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);">'
        f'<div>'
        f'<div style="font-size: 30px; font-weight: 900; letter-spacing: -0.5px; margin-bottom: 6px;">'
        f'🏠 Gdzie<span style="color: #fef08a;">Lokum</span>'
        f'</div>'
        f'<div style="font-size: 14px; color: #e0f2fe;">Wszystkie oferty mieszkań, domów i działek w całej Polsce w jednym miejscu</div>'
        f'</div>'
        f'<div style="text-align: right; font-size: 13px; color: #bae6fd;">'
        f'<div>🔎 <strong>Otodom &bull; OLX &bull; Nieruchomości-online &bull; Biura</strong></div>'
        f'<div style="margin-top: 4px; color: #ffffff;">📍 Wyniki dla: <strong>{html.escape(city)}</strong> ({html.escape(property_type)})</div>'
        f'</div>'
        f'</div>'
    )
st.markdown(hero_html, unsafe_allow_html=True)

# =========================================================================
# WIDOK STANDARDOWY (DLA POSZUKUJĄCYCH)
# =========================================================================
if not is_pro:
    tab_offers, tab_market, tab_agencies, tab_favs = st.tabs([
        "Znalezione Oferty",
        "📊 Analiza Cen",
        "Lokalne Biura Nieruchomości",
        f"Zapisane Ulubione ({len(st.session_state.favorites)})"
    ])

    with tab_offers:
        if not offers:
            st.warning("Brak ofert spełniających podane kryteria. Spróbuj zwiększyć budżet.")
        else:
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Wszystkie oferty", len(offers))
            c2.metric("Otodom", sum(1 for o in offers if o.get("source") == "Otodom"))
            c3.metric("OLX", sum(1 for o in offers if o.get("source") == "OLX"))
            c4.metric("Nieruchomości-online", sum(1 for o in offers if o.get("source") == "Nieruchomości-online"))
            c5.metric("Gratka / Biura", sum(1 for o in offers if o.get("source") not in ["Otodom", "OLX", "Nieruchomości-online"]))
            
            st.markdown("---")
            cols = st.columns(2)
            for idx, ad in enumerate(offers):
                with cols[idx % 2]:
                    with st.container(border=True):
                        ci, cd = st.columns([1, 2])
                        with ci:
                            if ad.get("image"):
                                st.image(ad["image"], use_container_width=True)
                            else:
                                st.markdown("""
                                <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); height: 130px; display: flex; flex-direction: column; align-items: center; justify-content: center; border-radius: 8px; color: #64748b; font-size: 11px; text-align: center; padding: 6px; border: 1px dashed #cbd5e1;">
                                    <span style="font-size: 24px; margin-bottom: 4px;">📷</span>
                                    <span>Brak zdjęć<br>w ofercie</span>
                                </div>
                                """, unsafe_allow_html=True)
                        with cd:
                            src = html.escape(str(ad.get("source", "")))
                            badge_cls = "badge-otodom" if src == "Otodom" else ("badge-olx" if src == "OLX" else ("badge-no" if src == "Nieruchomości-online" else "badge-agency"))
                            
                            deal_badge = ""
                            if ad.get("deal_tag"):
                                deal_badge = f'<span class="{ad.get("deal_class")}">{html.escape(str(ad.get("deal_tag")))}</span>'
                                
                            title = html.escape(str(ad.get("title", "Oferta")))
                            url = ad.get("url", "#")
                            
                            tot = ad.get("total_price", 0)
                            base = ad.get("base_price", 0)
                            admin = ad.get("admin_fee", 0)
                            
                            if admin and admin > 0 and cat_key == "wynajem":
                                price_line = f'<div class="price-total">{tot:,} zł <span style="font-size:13px; font-weight:normal; color:#64748b;">ze wszystkim</span></div>'.replace(',', ' ')
                                price_line += f'<div class="price-breakdown">(Odstępne: {base:,} zł + Czynsz: {admin:,} zł)</div>'.replace(',', ' ')
                            else:
                                if isinstance(base, (int, float)) and base > 0:
                                    price_line = f'<div class="price-total">{base:,} zł</div>'.replace(',', ' ')
                                else:
                                    price_line = f'<div class="price-total">{html.escape(str(base))}</div>'
                                    
                            loc = html.escape(str(ad.get("location", "")))
                            area = ad.get("area", 0)
                            pm2 = ad.get("price_per_m2")
                            meta_parts = []
                            if area: meta_parts.append(f"📏 {area} m²")
                            if pm2: meta_parts.append(f"💰 {pm2:,.0f} zł/m²".replace(',', ' '))
                            if ad.get("rooms"): meta_parts.append(f"🚪 {html.escape(str(ad.get('rooms')))}")
                            meta_str = " | ".join(meta_parts)
                            meta_html = f"<div style='font-size:13px; color:#334155; margin-top:4px;'>{meta_str}</div>" if meta_str else ""
                            loc_html = f'<div class="loc-tag">📍 {loc}</div>' if loc else ""
                            
                            card_html = (
                                f'<div class="notranslate" translate="no">'
                                f'<div style="margin-bottom:6px;"><span class="badge {badge_cls}">{src}</span>{deal_badge}</div>'
                                f'<div style="margin-bottom:6px; font-size:15px; font-weight:700; line-height:1.3;"><a href="{url}" target="_blank" style="text-decoration:none; color:#0f172a;">{title}</a></div>'
                                f'{price_line}'
                                f'{meta_html}'
                                f'{loc_html}'
                                f'</div>'
                            )
                            st.markdown(card_html, unsafe_allow_html=True)

                        b1, b2 = st.columns([2, 1])
                        with b1:
                            st.link_button("🔗 Otwórz ofertę", ad.get("url", "#"), use_container_width=True)
                        with b2:
                            is_fav = any(f.get("url") == ad.get("url") for f in st.session_state.favorites)
                            if st.button("❤️ Zapisane" if is_fav else "🤍 Zapisz", key=f"fav_{idx}_{ad.get('id', '')}", use_container_width=True):
                                if is_fav:
                                    st.session_state.favorites = [f for f in st.session_state.favorites if f.get("url") != ad.get("url")]
                                else:
                                    st.session_state.favorites.append(ad)
                                st.rerun()

    with tab_market:
        st.subheader(f"📊 Analiza cen rynkowych: {city} ({property_type})")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Średnia cena za m²", f"{market_stats['avg_m2']:,.0f} zł".replace(',', ' ') if market_stats['avg_m2'] else "Brak danych")
        m2.metric("Mediana za m²", f"{market_stats['median_m2']:,.0f} zł".replace(',', ' ') if market_stats['median_m2'] else "Brak danych")
        m3.metric("Najtańszy m²", f"{market_stats['min_m2']:,.0f} zł".replace(',', ' ') if market_stats['min_m2'] else "Brak danych")
        m4.metric("Najdroższy m²", f"{market_stats['max_m2']:,.0f} zł".replace(',', ' ') if market_stats['max_m2'] else "Brak danych")
        
        st.info("💡 Oferty z oznaczeniem '🔥 Poniżej średniej' to statystyczne okazje cenowe w stosunku do średniej w tym mieście.")

    with tab_agencies:
        st.subheader(f"📍 Biura Nieruchomości w regionie: {city}")
        for ag in load_local_agencies(city):
            with st.container(border=True):
                ca, cb = st.columns([3, 1])
                with ca:
                    st.markdown(f"### {ag.get('name')}")
                    st.write(f"📍 {ag.get('address')} | 📞 `{ag.get('phone')}` | 🌐 [{ag.get('website')}]({ag.get('website')})")
                with cb:
                    st.link_button("📂 Baza Ofert", ag.get("rentals_url", ag.get("website")), use_container_width=True)

    with tab_favs:
        st.subheader("⭐ Zapisane nieruchomości")
        if not st.session_state.favorites:
            st.info("Nie masz jeszcze zapisanych ofert.")
        else:
            for f in st.session_state.favorites:
                with st.container(border=True):
                    f1, f2, f3 = st.columns([3, 1, 1])
                    with f1:
                        st.markdown(f"**[{f.get('title')}]({f.get('url')})**")
                        st.caption(f"{f.get('source')} | {f.get('location')}")
                    with f2:
                        st.markdown(f"**{f.get('total_price'):,} zł**".replace(',', ' '))
                    with f3:
                        st.link_button("🔗 Otwórz", f.get("url"), use_container_width=True)

# =========================================================================
# WIDOK PRO DLA BIUR NIERUCHOMOŚCI I POŚREDNIKÓW
# =========================================================================
else:
    tab_leads, tab_pricing, tab_report, tab_mls, tab_partners = st.tabs([
        "🎯 Pozyskiwanie Ofert (Leady)",
        "📊 Analizator Rynku & Wyceny",
        "📄 Generator Raportu dla Klienta (PDF)",
        "🤝 Giełda Współpracy MLS",
        "👑 Certyfikowane Biura"
    ])

    # 1. POZYSKIWANIE OFERT (LEAD SOURCING & CRM)
    with tab_leads:
        st.subheader("🎯 Baza Ofert Bezpośrednich do Pozyskania")
        st.write("Oferty wystawione bezpośrednio przez właścicieli (prywatne). Skontaktuj się z nimi, aby podpisać umowę pośrednictwa:")
        
        # Filtruj tylko prywatne
        private_leads = [o for o in offers if o.get("is_private") or o.get("source") == "OLX"]
        
        st.metric("Ofert prywatnych w rejonie", len(private_leads))
        st.markdown("---")
        
        for idx, lead in enumerate(private_leads[:20]):
            with st.container(border=True):
                l_info, l_crm = st.columns([3, 2])
                with l_info:
                    st.markdown(f"**[{lead.get('title')}]({lead.get('url')})**")
                    st.markdown(f"💰 **Cena:** {lead.get('total_price'):,} zł | 📍 **Lokalizacja:** {lead.get('location')}".replace(',', ' '))
                    st.caption(f"Źródło: {lead.get('source')} | Dodano: {lead.get('date', 'Niedawno')}")
                    st.link_button("📞 Otwórz ogłoszenie / Sprawdź telefon", lead.get("url"), use_container_width=False)
                
                with l_crm:
                    st.markdown("**Status pozyskania w CRM:**")
                    cur_status = get_lead_status(lead.get("id", str(idx)))
                    status_opts = ["Do kontaktu", "Zadzwoniono - brak odp.", "Spotkanie umówione", "Umowa podpisana", "Odrzucono"]
                    cur_idx = status_opts.index(cur_status.get("status")) if cur_status.get("status") in status_opts else 0
                    
                    new_st = st.selectbox("Status kontaktu", status_opts, index=cur_idx, key=f"crm_st_{idx}_{lead.get('id', '')}")
                    new_note = st.text_input("Notatka agenta", value=cur_status.get("note", ""), placeholder="np. Właściciel otwarty na wyłączność", key=f"crm_nt_{idx}_{lead.get('id', '')}")
                    
                    if new_st != cur_status.get("status") or new_note != cur_status.get("note"):
                        save_crm_status(lead.get("id", str(idx)), new_st, new_note)
                        st.success("Zapisano w CRM!")

    # 2. ANALIZA CEN RYNKOWYCH
    with tab_pricing:
        st.subheader(f"📊 Raport Wyceny Rynkowej: {city}")
        st.write("Aktualne dane cenowe z rynku nieruchomości do rozmów z właścicielami i klientami:")
        
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Średnia cena za m²", f"{market_stats['avg_m2']:,.0f} zł".replace(',', ' ') if market_stats['avg_m2'] else "-")
        c_m2.metric("Mediana cenowa m²", f"{market_stats['median_m2']:,.0f} zł".replace(',', ' ') if market_stats['median_m2'] else "-")
        c_m3.metric("Średnia cena łączna", f"{market_stats['avg_total']:,.0f} zł".replace(',', ' ') if market_stats['avg_total'] else "-")
        
        st.markdown("---")
        st.markdown("#### 🔥 Wykryte okazje cenowe (poniżej średniej rynkowej):")
        deals = [o for o in offers if o.get("deal_class") == "deal-good"]
        if deals:
            for d in deals[:6]:
                with st.container(border=True):
                    d1, d2 = st.columns([4, 1])
                    with d1:
                        st.markdown(f"**[{d.get('title')}]({d.get('url')})**")
                        st.write(f"Cena: **{d.get('total_price'):,} zł** | Metraż: **{d.get('area')} m²** | Cena m²: **{d.get('price_per_m2'):,.0f} zł/m²** ({d.get('diff_pct')}% poniżej rynku!)".replace(',', ' '))
                    with d2:
                        st.link_button("Zobacz", d.get("url"), use_container_width=True)
        else:
            st.info("Wszystkie oferty mieszczą się w normie rynkowej.")

    # 3. GENERATOR RAPORTU DLA KLIENTA (PDF / DRUK)
    with tab_report:
        st.subheader("📄 Generator Raportu / Prezentacji Ofert dla Klienta")
        st.write("Wybierz oferty z rynku i wygeneruj elegancki katalog ofert ze swoim logo i kontaktem do wydruku lub wysyłki w PDF:")
        
        col_ag_form, col_ag_preview = st.columns([1, 2])
        
        with col_ag_form:
            with st.container(border=True):
                st.markdown("#### Twoje dane biura:")
                rep_agency = st.text_input("Nazwa Twojego Biura", value="Karkonosze Nieruchomości")
                rep_agent = st.text_input("Imię i nazwisko doradcy", value="Jan Kowalski")
                rep_phone = st.text_input("Numer telefonu", value="+48 600 123 456")
                rep_email = st.text_input("Adres e-mail", value="biuro@karkonoszenieruchomosci.pl")
                rep_client = st.text_input("Przygotowano dla klienta (imię/nazwisko)", value="Piotr Nowak")
                st.markdown("#### Wybierz oferty do raportu:")
                offer_titles = {f"{i+1}. {o.get('title', 'Oferta')} ({o.get('source')}, {o.get('total_price', 0):,} zł)".replace(',', ' '): o for i, o in enumerate(offers[:25])}
                selected_titles = st.multiselect("Zaznacz oferty dla klienta:", list(offer_titles.keys()), default=list(offer_titles.keys())[:3] if len(offer_titles) >= 3 else list(offer_titles.keys()))
                selected_offers = [offer_titles[t] for t in selected_titles if t in offer_titles]

        with col_ag_preview:
            if selected_offers:
                st.success(f"Wybrano **{len(selected_offers)}** ofert do zestawienia.")
                report_html = generate_client_catalog_html(
                    agency_name=rep_agency,
                    agent_name=rep_agent,
                    agent_phone=rep_phone,
                    agency_email=rep_email,
                    client_name=rep_client,
                    selected_offers=selected_offers
                )
                
                # Zapisz plik raportu do pobrania
                st.download_button(
                    label="📥 Pobierz Raport Klienta (Plik HTML / PDF)",
                    data=report_html,
                    file_name=f"Raport_Ofert_{rep_client.replace(' ', '_')}.html",
                    mime="text/html",
                    use_container_width=True,
                    type="primary"
                )
                
                st.caption("Podgląd prezentacji (w oknie poniżej):")
                components.html(report_html, height=550, scrolling=True)
            else:
                st.info("Zaznacz przynajmniej 1 ofertę, aby wygenerować raport.")

    # 4. GIEŁDA WSPÓŁPRACY MLS
    with tab_mls:
        st.subheader("🤝 Giełda Współpracy Międzybiurowej (MLS)")
        st.write("Oferty agencyjne zgłoszone do współpracy z innymi pośrednikami (podział prowizji 50/50):")
        
        agency_offers = [o for o in offers if o.get("source") not in ["Otodom", "OLX", "Nieruchomości-online"] or "Biuro" in o.get("advertiser", "")]
        st.metric("Ofert do współpracy agencyjnej", len(agency_offers))
        st.markdown("---")
        
        for ao in agency_offers[:10]:
            with st.container(border=True):
                c_mls1, c_mls2 = st.columns([4, 1])
                with c_mls1:
                    st.markdown(f"**[{ao.get('title')}]({ao.get('url')})**")
                    st.markdown(f"🏢 Agencja zgłaszająca: **{ao.get('advertiser', 'Biuro Nieruchomości')}** | Cena: **{ao.get('total_price'):,} zł**".replace(',', ' '))
                    st.markdown("""<span style="background:#dcfce7; color:#15803d; padding:2px 8px; border-radius:4px; font-weight:700; font-size:12px;">🤝 Współpraca 50/50: TAK</span>""", unsafe_allow_html=True)
                with c_mls2:
                    st.link_button("Skontaktuj się", ao.get("url"), use_container_width=True)

    # 5. CERTYFIKOWANE BIURA PARTNERSKIE
    with tab_partners:
        st.subheader("👑 Certyfikowane Biura Partnerskie GdzieLokum")
        st.write("Agencje posiadające status Zweryfikowanego Partnera w regionie:")
        
        partners = load_local_agencies(city)
        for p in partners:
            with st.container(border=True):
                cp1, cp2 = st.columns([3, 1])
                with cp1:
                    st.markdown(f"### 🛡️ {p.get('name')}")
                    st.write(f"📍 {p.get('address')} | 📞 `{p.get('phone')}`")
                    st.markdown("""<span class="badge badge-pro">👑 ZWERYFIKOWANY PARTNER</span> <span class="badge badge-no">Ubezpieczenie OC</span>""", unsafe_allow_html=True)
                with cp2:
                    st.link_button("Strona Biura", p.get("website"), use_container_width=True)

# STOPKA GDZIELOKUM
footer_html = (
    '<div class="notranslate" translate="no" style="margin-top: 50px; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 13px;">'
    '<strong>🏠 GdzieLokum &bull; GdzieLokum PRO</strong> &copy; 2026 Wszystkie prawa zastrzeżone.<br>'
    '<span style="font-size: 11px; color: #94a3b8;">Inteligentny Agregator Nieruchomości w Polsce (Otodom, OLX, Nieruchomości-online, Gratka & Biura).</span>'
    '</div>'
)
st.markdown(footer_html, unsafe_allow_html=True)

