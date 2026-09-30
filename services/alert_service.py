import json
from datetime import datetime
from typing import Dict, Any, List
from db.database import get_connection

def check_offers_against_alerts(offers: List[Dict[str, Any]], city: str) -> List[Dict[str, Any]]:
    """
    Sprawdza nowo pobrane oferty z bazy/agregatora pod kątem aktywnych alertów użytkowników (Snajper Okazji).
    Zwraca wygenerowane powiadomienia o okazjach inwestycyjnych.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT * FROM search_alerts
    WHERE city = ? AND is_active = 1;
    """, (city.lower(),))
    alerts = [dict(r) for r in cur.fetchall()]
    conn.close()

    triggered_notifications = []

    for alert in alerts:
        max_p = alert.get("max_price")
        min_a = alert.get("min_area")
        min_r = alert.get("min_rooms")
        min_disc = alert.get("min_discount_pct", 10.0)

        for o in offers:
            # Sprawdź warunki
            price = o.get("total_price") or 0
            area = o.get("area") or 0
            diff_pct = o.get("diff_pct") or 0
            score = o.get("score") or 50

            if max_p and price > max_p:
                continue
            if min_a and area < min_a:
                continue
            
            # Warunek okazji cenowej (np. min. 10% poniżej mediany)
            if diff_pct > -min_disc:
                continue

            # Alert spełniony!
            notification_text = (
                f"🚨 **NOWA OKAZJA INWESTYCYJNA!**\n\n"
                f"📍 **Lokalizacja:** {o.get('location', city.capitalize())}\n"
                f"🚪 **Pokoje:** {o.get('rooms', 'B/D')} | 📐 **Metraż:** {area} m²\n"
                f"💰 **Cena:** {price:,} zł ({o.get('price_per_m2', 0):,.0f} zł/m²)\n"
                f"📊 **Różnica rynkowa:** {diff_pct}%\n"
                f"⭐ **GdzieLokum SCORE:** {score}/100"
            ).replace(",", " ")

            triggered_notifications.append({
                "alert_id": alert.get("id"),
                "recipient_email": alert.get("email"),
                "recipient_phone": alert.get("phone"),
                "channel": alert.get("channel", "email"),
                "message": notification_text,
                "property_id": o.get("id"),
                "property_url": o.get("url"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    return triggered_notifications
