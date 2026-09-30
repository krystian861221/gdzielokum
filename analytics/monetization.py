import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from db.database import get_connection

BANK_ACCOUNT_NUMBER = "17 2910 0006 2469 8002 0024 1917"
BANK_RECIPIENT_NAME = "GdzieLokum"

def calculate_mortgage_installment(
    price: float,
    down_payment_pct: float = 10.0,
    years: int = 30,
    interest_rate: float = 7.2
) -> Dict[str, Any]:
    if price <= 0:
        return {'monthly': 0, 'down_payment': 0, 'loan_amount': 0}
        
    down_payment = round(price * (down_payment_pct / 100.0), 2)
    loan_amount = price - down_payment
    
    n_months = years * 12
    monthly_r = (interest_rate / 100.0) / 12.0
    
    if monthly_r == 0 or n_months == 0:
        monthly_payment = round(loan_amount / max(1, n_months), 2)
    else:
        factor = (1 + monthly_r) ** n_months
        monthly_payment = round(loan_amount * (monthly_r * factor) / (factor - 1), 2)
        
    return {
        'monthly': monthly_payment,
        'down_payment': down_payment,
        'loan_amount': loan_amount,
        'interest_rate': interest_rate,
        'years': years
    }

def save_mortgage_lead(
    name: str,
    phone: str,
    email: str,
    city: str,
    property_price: float,
    down_payment: float = 0.0,
    loan_period_years: int = 30,
    notes: str = '',
    rodo_consent: bool = True
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO mortgage_leads (
        name, phone, email, city, property_price, down_payment, loan_period_years, rodo_consent, notes, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Nowy');
    """, (name, phone, email, city, property_price, down_payment, loan_period_years, 1 if rodo_consent else 0, notes))
    lid = cur.lastrowid
    conn.commit()
    conn.close()
    return lid

def get_all_mortgage_leads() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM mortgage_leads ORDER BY created_at DESC;")
    leads = [dict(r) for r in cur.fetchall()]
    conn.close()
    return leads

def update_mortgage_lead_status(lead_id: int, status: str, partner_id: Optional[int] = None, commission_value: float = 0.0):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    UPDATE mortgage_leads
    SET status = ?, partner_id = COALESCE(?, partner_id), commission_value = ?
    WHERE id = ?;
    """, (status, partner_id, commission_value, lead_id))
    conn.commit()
    conn.close()

def save_agency_pro_order(
    agency_name: str,
    contact_person: str,
    phone: str,
    email: str,
    city: str,
    plan: str
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    # Stwórz wpis agency i subskrypcję trial 7 dni
    cur.execute("""
    INSERT INTO agencies (name, city, phone, email, subscription_plan)
    VALUES (?, ?, ?, ?, ?);
    """, (agency_name, city, phone, email, plan))
    agency_id = cur.lastrowid

    trial_end = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    cur.execute("""
    INSERT INTO subscriptions (agency_id, plan_id, status, trial_ends_at)
    VALUES (?, ?, 'trial', ?);
    """, (agency_id, plan, trial_end))
    conn.commit()
    conn.close()
    return agency_id

def get_marketplace_services(city: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM service_providers WHERE is_verified = 1;")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    if not rows:
        # Domyślni certyfikowani partnerzy ekosystemu
        return [
            {"category": "Kredyty hipoteczne", "company_name": "Notus / eBroker Finanse", "contact_phone": "+48 22 100 20 30", "description": "Porównanie ofert 12 banków, 0 zł prowizji od klienta.", "rating": 4.9},
            {"category": "Kancelaria Notarialna", "company_name": "Kancelaria Notarialna Lex", "contact_phone": "+48 71 340 50 60", "description": "Sprawna obsługa umów przedwstępnych i przeniesienia własności.", "rating": 5.0},
            {"category": "Rzeczoznawca Majątkowy", "company_name": "Wyceny Nieruchomości Pro", "contact_phone": "+48 600 700 800", "description": "Operaty szacunkowe akceptowane przez wszystkie banki w 48h.", "rating": 4.8},
            {"category": "Ubezpieczenia Nieruchomości", "company_name": "PZU / Warta Bezpieczny Dom", "contact_phone": "+48 22 555 44 33", "description": "Ubezpieczenie murów i stałych elementów pod cesję kredytu.", "rating": 4.9},
            {"category": "Remonty i Wykończenia", "company_name": "Solidne Wnętrza Sp. z o.o.", "contact_phone": "+48 690 112 233", "description": "Kompleksowe remonty pod klucz dla inwestorów i osób prywatnych.", "rating": 4.7}
        ]
    return rows
