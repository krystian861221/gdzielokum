from typing import Dict, Any, Optional

SCORE_DISCLAIMER = (
    "GdzieLokum SCORE jest wskaźnikiem analitycznym opartym na dostępnych danych rynkowych "
    "i nie stanowi gwarancji opłacalności inwestycji."
)

def calculate_gdzielokum_score(
    offer: Dict[str, Any],
    market_stats: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Wylicza zbalansowany, obiektywny GdzieLokum SCORE w skali 0–100 na bazie:
    - 40% Odchylenie ceny za m2 względem lokalnej mediany rynkowej
    - 20% Rentowność inwestycyjna (szacunkowy yield z najmu m2 vs cena zakupu)
    - 15% Powierzchnia i ergonomia (układ pokoi vs m2)
    - 15% Cechy dodatkowe (balkon, garaż, winda, taras)
    - 10% Świeżość oferty na rynku (premiowanie nowych ogłoszeń)
    """
    if weights is None:
        weights = {
            "price_diff": 0.40,
            "investment_yield": 0.20,
            "layout_ergonomics": 0.15,
            "amenities": 0.15,
            "freshness": 0.10
        }

    sub_scores = {}
    
    # 1. Odchylenie cenowe od mediany rynkowej (0-100)
    pm2 = offer.get("price_per_m2")
    median_m2 = market_stats.get("median_m2", 0)
    if pm2 and median_m2 and median_m2 > 0:
        diff_pct = ((pm2 - median_m2) / median_m2) * 100.0
        offer["diff_pct"] = round(diff_pct, 1)
        # diff_pct = -25% -> 100 pkt; diff_pct = 0% -> 65 pkt; diff_pct = +25% -> 30 pkt; +50% -> 10 pkt
        score_price = max(5.0, min(100.0, 65.0 - (diff_pct * 1.4)))
    else:
        diff_pct = 0.0
        score_price = 50.0
    sub_scores["price_score"] = round(score_price, 1)

    # 2. Szacowany potencjał inwestycyjny / yield najmu (0-100)
    # Szacujemy referencyjny czynsz najmu: ~40-60 zł/m2 w zależności od standardu
    area = offer.get("area") or 0.0
    tot_price = offer.get("total_price") or 0.0
    if area > 15 and tot_price > 50000:
        est_monthly_rent = area * 50.0 # ~50 zł / m2
        annual_yield = ((est_monthly_rent * 12) / tot_price) * 100.0
        offer["estimated_yield"] = round(annual_yield, 2)
        # 8% yield -> 95 pkt; 6% -> 70 pkt; 4% -> 45 pkt
        score_yield = max(10.0, min(100.0, (annual_yield / 8.0) * 90.0))
    else:
        annual_yield = 0.0
        score_yield = 50.0
    sub_scores["yield_score"] = round(score_yield, 1)

    # 3. Układ pokoi i metraż (ergonomia) (0-100)
    rooms = offer.get("rooms")
    if isinstance(rooms, str):
        try:
            rooms = int(''.join(filter(str.isdigit, rooms)))
        except Exception:
            rooms = 0
    if rooms and area:
        m2_per_room = area / max(1, rooms)
        # Optymalnie: 18-25 m2 na pokój
        if 16 <= m2_per_room <= 28:
            score_layout = 85.0
        elif 12 <= m2_per_room < 16 or 28 < m2_per_room <= 35:
            score_layout = 70.0
        else:
            score_layout = 55.0
    else:
        score_layout = 60.0
    sub_scores["layout_score"] = score_layout

    # 4. Udogodnienia (balkon, garaż, winda, stan) (0-100)
    amenity_pts = 50.0
    t_lower = (offer.get("title", "") + " " + offer.get("description", "")).lower()
    if offer.get("has_balcony") or "balkon" in t_lower:
        amenity_pts += 12.0
    if offer.get("has_garage") or "garaż" in t_lower or "miejsce postojowe" in t_lower or "parking" in t_lower:
        amenity_pts += 15.0
    if offer.get("has_elevator") or "winda" in t_lower:
        amenity_pts += 12.0
    if offer.get("has_garden") or "ogród" in t_lower or "ogródek" in t_lower:
        amenity_pts += 10.0
    sub_scores["amenities_score"] = min(100.0, amenity_pts)

    # 5. Czas publikacji (świeżość) (0-100)
    date_str = str(offer.get("date", "")).lower()
    if "dzisiaj" in date_str or "godz" in date_str or "niedawno" in date_str:
        score_fresh = 95.0
    elif "wczoraj" in date_str:
        score_fresh = 80.0
    else:
        score_fresh = 65.0
    sub_scores["freshness_score"] = score_fresh

    # Łączny ważony SCORE (0-100)
    final_score = (
        sub_scores["price_score"] * weights["price_diff"] +
        sub_scores["yield_score"] * weights["investment_yield"] +
        sub_scores["layout_score"] * weights["layout_ergonomics"] +
        sub_scores["amenities_score"] * weights["amenities"] +
        sub_scores["freshness_score"] * weights["freshness"]
    )
    final_score = int(round(max(5, min(99, final_score))))
    offer["score"] = final_score

    # Klasyfikacja wg specyfikacji GdzieLokum 2.0:
    # 0–39 — wymaga szczegółowej analizy
    # 40–59 — przeciętna oferta
    # 60–74 — interesująca
    # 75–89 — bardzo interesująca
    # 90–100 — wyjątkowo interesująca
    if final_score >= 90:
        label = "Wyjątkowo interesująca"
        color = "#15803d" # dark green
        badge_bg = "#dcfce7"
    elif final_score >= 75:
        label = "Bardzo interesująca"
        color = "#16a34a" # green
        badge_bg = "#bbf7d0"
    elif final_score >= 60:
        label = "Interesująca"
        color = "#0284c7" # blue
        badge_bg = "#e0f2fe"
    elif final_score >= 40:
        label = "Przeciętna oferta"
        color = "#d97706" # amber
        badge_bg = "#fef3c7"
    else:
        label = "Wymaga szczegółowej analizy"
        color = "#dc2626" # red
        badge_bg = "#fee2e2"

    return {
        "score": final_score,
        "label": label,
        "color": color,
        "badge_bg": badge_bg,
        "sub_scores": sub_scores,
        "diff_pct": diff_pct,
        "disclaimer": SCORE_DISCLAIMER
    }
