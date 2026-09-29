from typing import List, Dict, Any

def analyze_market_prices(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analizuje ceny i metraże ofert w zadanym zbiorze,
    wylicza średnią cenę za m2, medianę, min/max oraz oznacza okazje cenowe.
    """
    valid_m2_offers = []
    prices_m2 = []
    total_prices = []

    for o in offers:
        price = o.get("total_price", 0)
        area = o.get("area", 0)
        if isinstance(price, (int, float)) and price > 0:
            total_prices.append(price)
            if isinstance(area, (int, float)) and area > 10:
                m2_price = round(price / area, 2)
                o["price_per_m2"] = m2_price
                prices_m2.append(m2_price)
                valid_m2_offers.append(o)
            else:
                o["price_per_m2"] = None
        else:
            o["price_per_m2"] = None

    if not prices_m2:
        return {
            "avg_m2": 0,
            "median_m2": 0,
            "min_m2": 0,
            "max_m2": 0,
            "avg_total": round(sum(total_prices) / len(total_prices), 2) if total_prices else 0,
            "total_count": len(offers),
            "analyzed_count": 0
        }

    prices_m2.sort()
    avg_m2 = round(sum(prices_m2) / len(prices_m2), 2)
    median_m2 = prices_m2[len(prices_m2) // 2]
    min_m2 = prices_m2[0]
    max_m2 = prices_m2[-1]
    avg_total = round(sum(total_prices) / len(total_prices), 2) if total_prices else 0

    # Oznacz każdą ofertę wskaźnikiem atrakcyjności cenowej
    for o in offers:
        pm2 = o.get("price_per_m2")
        if pm2 and avg_m2 > 0:
            diff_pct = round(((pm2 - avg_m2) / avg_m2) * 100, 1)
            o["diff_pct"] = diff_pct
            if diff_pct <= -12:
                o["deal_tag"] = "🔥 Poniżej średniej (Okazja!)"
                o["deal_class"] = "deal-good"
            elif diff_pct >= 15:
                o["deal_tag"] = "📈 Powyżej średniej"
                o["deal_class"] = "deal-high"
            else:
                o["deal_tag"] = "⚖️ Cena rynkowa"
                o["deal_class"] = "deal-mid"
        else:
            o["deal_tag"] = None

    return {
        "avg_m2": avg_m2,
        "median_m2": median_m2,
        "min_m2": min_m2,
        "max_m2": max_m2,
        "avg_total": avg_total,
        "total_count": len(offers),
        "analyzed_count": len(prices_m2)
    }
