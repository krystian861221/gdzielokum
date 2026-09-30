import html
from typing import List, Dict, Any

def generate_client_catalog_html(
    agency_name: str,
    agent_name: str,
    agent_phone: str,
    agency_email: str,
    client_name: str,
    selected_offers: List[Dict[str, Any]]
) -> str:
    """
    Generuje elegancki, gotowy do druku lub zapisu jako PDF katalog ofert dla klienta.
    Zawiera dane biura, zdjęcia, parametry, analizę rynkową oraz GdzieLokum SCORE.
    Całkowicie pozbawiony linków do zewnętrznych portali ogłoszeniowych.
    """
    offers_html = ""
    for idx, o in enumerate(selected_offers, 1):
        img_src = o.get("image")
        if img_src and "http" in img_src:
            img_tag = f'<img src="{img_src}" style="width: 100%; height: 220px; object-fit: cover; border-radius: 8px;">'
        else:
            img_tag = '<div style="width:100%; height:220px; background:#f1f5f9; display:flex; align-items:center; justify-content:center; border-radius:8px; font-size:32px;">🏡</div>'
        
        price_raw = o.get("total_price")
        price_str = f"{int(price_raw):,} zł".replace(',', ' ') if price_raw and isinstance(price_raw, (int, float)) and price_raw > 0 else "Zapytaj o cenę"
        area = f"{o.get('area')} m²" if o.get('area') else "B/D"
        rooms = f"{o.get('rooms')} pok." if o.get('rooms') else "B/D"
        loc = o.get('location', "")
        pm2_val = o.get('price_per_m2')
        pm2 = f"{float(pm2_val):,.0f} zł/m²".replace(',', ' ') if pm2_val and isinstance(pm2_val, (int, float)) and pm2_val > 0 else "B/D"
        score = o.get('score', 75)
        diff_pct = o.get('diff_pct', 0)
        diff_badge = f'<span style="background:#dcfce7; color:#15803d; padding:2px 8px; border-radius:4px; font-weight:700; font-size:12px;">{diff_pct}% względem rynku</span>' if diff_pct and isinstance(diff_pct, (int, float)) and diff_pct < 0 else f'<span style="background:#f1f5f9; color:#475569; padding:2px 8px; border-radius:4px; font-size:12px;">Cena rynkowa</span>'

        offers_html += f"""
        <div class="offer-box">
            <div class="offer-header">
                <span class="offer-num">Propozycja #{idx}</span>
                <div>
                    <span style="background:#e0f2fe; color:#0369a1; padding:3px 8px; border-radius:4px; font-weight:700; font-size:12px; margin-right:8px;">GdzieLokum SCORE: {score}/100</span>
                    {diff_badge}
                    <span class="offer-price" style="margin-left:12px;">{price_str}</span>
                </div>
            </div>
            <div class="offer-content">
                <div class="offer-img-col">
                    {img_tag}
                </div>
                <div class="offer-desc-col">
                    <h3 class="offer-title">{html.escape(o.get('title', 'Nieruchomość'))}</h3>
                    <div class="offer-meta">
                        <strong>Metraż:</strong> {area} | <strong>Pokoje:</strong> {rooms} | <strong>Cena m²:</strong> {pm2} | <strong>Lokalizacja:</strong> {loc}
                    </div>
                    <div class="offer-features">
                        <p>Starannie wyselekcjonowana oferta dopasowana do Państwa preferencji poszukiwania. W celu umówienia bezpośredniej prezentacji nieruchomości lub uzyskania szczegółowej dokumentacji prawnej prosimy o bezpośredni kontakt z opiekunem oferty.</p>
                    </div>
                </div>
            </div>
        </div>
        """

    full_html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>Zestawienie Ofert - {html.escape(client_name)}</title>
<style>
    @page {{
        size: A4;
        margin: 15mm;
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #1e293b;
        background: #ffffff;
        margin: 0;
        padding: 20px;
    }}
    .no-print-bar {{
        background: #0f172a;
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .print-btn {{
        background: #dc2626;
        color: white;
        border: none;
        padding: 10px 20px;
        font-size: 15px;
        font-weight: 600;
        border-radius: 6px;
        cursor: pointer;
    }}
    .print-btn:hover {{ background: #b91c1c; }}
    .header {{
        border-bottom: 3px solid #dc2626;
        padding-bottom: 20px;
        margin-bottom: 30px;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }}
    .agency-name {{
        font-size: 26px;
        font-weight: 800;
        color: #0f172a;
        margin: 0 0 6px 0;
    }}
    .agency-contact {{
        font-size: 14px;
        color: #475569;
        line-height: 1.5;
    }}
    .catalog-title {{
        text-align: right;
    }}
    .catalog-title h2 {{
        margin: 0 0 6px 0;
        color: #dc2626;
        font-size: 20px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .catalog-title p {{
        margin: 0;
        color: #64748b;
        font-size: 14px;
    }}
    .offer-box {{
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 26px;
        page-break-inside: avoid;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }}
    .offer-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 10px;
        margin-bottom: 14px;
    }}
    .offer-num {{
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        color: #64748b;
    }}
    .offer-price {{
        font-size: 22px;
        font-weight: 800;
        color: #16a34a;
    }}
    .offer-content {{
        display: flex;
        gap: 20px;
    }}
    .offer-img-col {{
        flex: 0 0 260px;
    }}
    .offer-desc-col {{
        flex: 1;
    }}
    .offer-title {{
        font-size: 17px;
        font-weight: 700;
        margin: 0 0 10px 0;
        color: #0f172a;
        line-height: 1.3;
    }}
    .offer-meta {{
        font-size: 14px;
        color: #334155;
        background: #f8fafc;
        padding: 8px 12px;
        border-radius: 6px;
        margin-bottom: 12px;
    }}
    .offer-features p {{
        font-size: 13px;
        color: #64748b;
        line-height: 1.6;
        margin: 0;
    }}
    .footer {{
        border-top: 1px solid #e2e8f0;
        padding-top: 16px;
        margin-top: 30px;
        text-align: center;
        font-size: 12px;
        color: #94a3b8;
    }}
    @media print {{
        .no-print-bar {{ display: none !important; }}
        body {{ padding: 0; }}
        .offer-box {{ box-shadow: none; }}
    }}
</style>
</head>
<body>

<div class="no-print-bar">
    <div>
        <strong>Podgląd Raportu Klienta</strong> &bull; Kliknij przycisk obok, aby zapisać jako PDF lub wydrukować.
    </div>
    <button class="print-btn" onclick="window.print()">🖨️ Drukuj / Zapisz jako PDF</button>
</div>

<div class="header">
    <div>
        <h1 class="agency-name">{html.escape(agency_name)}</h1>
        <div class="agency-contact">
            Opiekun klienta: <strong>{html.escape(agent_name)}</strong><br>
            Telefon: <strong>{html.escape(agent_phone)}</strong><br>
            Email: {html.escape(agency_email)}
        </div>
    </div>
    <div class="catalog-title">
        <h2>Dedykowany Raport Ofert</h2>
        <p>Przygotowano dla: <strong>{html.escape(client_name)}</strong></p>
    </div>
</div>

<div class="offers-list">
    {offers_html}
</div>

<div class="footer">
    Materiał przygotowany przez {html.escape(agency_name)} z wykorzystaniem systemu GdzieLokum 2.0 PRO. Wszelkie prawa zastrzeżone.<br>
    <span style="font-size:10px;">GdzieLokum SCORE jest wskaźnikiem analitycznym opartym na dostępnych danych rynkowych i nie stanowi gwarancji opłacalności inwestycji.</span>
</div>

</body>
</html>
"""
    return full_html
