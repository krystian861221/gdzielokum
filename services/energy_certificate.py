"""
Moduł obsługi i zamówień Świadectw Charakterystyki Energetycznej Budynków i Lokali.
Zgodność z nowelizacją ustawy o charakterystyce energetycznej budynków (Dz.U. 2022 poz. 2206).
"""

from typing import Dict, Any, List
from db.database import get_connection

CERTIFICATE_PACKAGES = [
    {
        "id": "flat",
        "title": "Mieszkanie / Lokal mieszkalny",
        "price_gross": 249,
        "delivery_time": "24h - 48h",
        "description": "Obowiązkowe do aktu notarialnego sprzedaży oraz każdej umowy najmu mieszkania.",
        "features": [
            "Wpis do Centralnego Rejestru MRiT (Ministerstwo Rozwoju i Technologii)",
            "Plik PDF z bezpiecznym podpisem kwalifikowanym audytora",
            "Certyfikowany audytor z uprawnieniami państwowymi",
            "Akceptowane przez wszystkich notariuszy w Polsce"
        ]
    },
    {
        "id": "house",
        "title": "Dom jednorodzinny",
        "price_gross": 399,
        "delivery_time": "24h - 48h",
        "description": "Niezbędne do sprzedaży domu, zawiadomienia o zakończeniu budowy lub wynajmu.",
        "features": [
            "Wpis do Centralnego Rejestru MRiT",
            "Zawiera wskaźniki EP, EK, EU oraz klasę energetyczną budynku",
            "Zalecenia dotyczące poprawy efektywności i termomodernizacji",
            "Wersja cyfrowa + gotowy wydruk do dokumentacji budowlanej"
        ]
    },
    {
        "id": "commercial",
        "title": "Lokal użytkowy / Budynek komercyjny",
        "price_gross": 649,
        "delivery_time": "48h - 72h",
        "description": "Dla lokali usługowych, handlowych, biurowych oraz obiektów wielorodzinnych.",
        "features": [
            "Pełna inwentaryzacja cieplna i bilans instalacji HVAC",
            "Rejestracja w centralnym rejestrze państwowym MRiT",
            "Wystawiamy fakturę VAT 23% dla firm i spółek"
        ]
    }
]

def save_energy_certificate_order(
    client_name: str,
    phone: str,
    email: str,
    city: str,
    property_type: str,
    area_m2: float,
    property_address: str,
    notes: str = ""
) -> int:
    """
    Zapisuje zamówienie na świadectwo charakterystyki energetycznej do bazy danych.
    """
    conn = get_connection()
    cur = conn.cursor()
    # Zapisujemy do leads z dedykowanym statusem
    cur.execute("""
    INSERT INTO leads (contact_name, contact_phone, contact_email, source, status, next_contact_date)
    VALUES (?, ?, ?, ?, 'Nowy - Świadectwo Energetyczne', datetime('now', '+2 hours'));
    """, (
        f"{client_name} [{property_type} {area_m2}m², {city}]",
        phone,
        email,
        f"Certyfikat Energetyczny ({property_address})"
    ))
    order_id = cur.lastrowid
    
    # Dodajemy notatkę ze szczegółami zamówienia
    cur.execute("""
    INSERT INTO crm_notes (lead_id, note)
    VALUES (?, ?);
    """, (
        order_id,
        f"ZAMÓWIENIE ŚWIADECTWA: Typ: {property_type}, Metraż: {area_m2} m², Adres: {property_address}, Uwagi: {notes}"
    ))
    conn.commit()
    conn.close()
    return order_id
