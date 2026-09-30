import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "gdzielokum.db")

def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 1. Users & Profiles
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        phone TEXT,
        full_name TEXT,
        role TEXT DEFAULT 'buyer',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        avatar_url TEXT,
        bio TEXT,
        city TEXT,
        preferences_json TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 2. Agencies & Agents
    cur.execute("""
    CREATE TABLE IF NOT EXISTS agencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE,
        description TEXT,
        city TEXT,
        address TEXT,
        phone TEXT,
        email TEXT,
        website TEXT,
        logo_url TEXT,
        is_verified BOOLEAN DEFAULT 0,
        subscription_plan TEXT DEFAULT 'free',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER,
        user_id INTEGER,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        license_nr TEXT,
        FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE SET NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    # 3. Properties & Sources
    cur.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        city TEXT NOT NULL,
        district TEXT,
        street TEXT,
        total_price REAL,
        area REAL,
        price_per_m2 REAL,
        rooms INTEGER,
        floor INTEGER,
        floors_total INTEGER,
        build_year INTEGER,
        property_type TEXT DEFAULT 'Mieszkanie',
        market_type TEXT DEFAULT 'wtórny',
        is_private BOOLEAN DEFAULT 0,
        has_balcony BOOLEAN DEFAULT 0,
        has_terrace BOOLEAN DEFAULT 0,
        has_garden BOOLEAN DEFAULT 0,
        has_garage BOOLEAN DEFAULT 0,
        has_elevator BOOLEAN DEFAULT 0,
        heating TEXT,
        building_condition TEXT,
        description TEXT,
        url TEXT,
        source TEXT,
        score INTEGER DEFAULT 50,
        score_details_json TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prop_city ON properties(city);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prop_price ON properties(total_price);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prop_m2 ON properties(price_per_m2);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prop_score ON properties(score);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS property_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT UNIQUE,
        is_enabled BOOLEAN DEFAULT 1,
        adapter_type TEXT,
        api_endpoint TEXT,
        api_key TEXT,
        last_sync DATETIME
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS property_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id TEXT,
        image_url TEXT NOT NULL,
        is_primary BOOLEAN DEFAULT 0,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS property_analysis (
        property_id TEXT PRIMARY KEY,
        local_median_m2 REAL,
        local_avg_m2 REAL,
        diff_pct REAL,
        deal_class TEXT,
        estimated_rent REAL,
        estimated_roi REAL,
        calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );
    """)

    # 4. Market Data Aggregates
    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        category TEXT,
        avg_m2 REAL,
        median_m2 REAL,
        min_m2 REAL,
        max_m2 REAL,
        offers_count INTEGER,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_market_city_cat ON market_data(city, category);")

    # 5. Saved Properties & Searches
    cur.execute("""
    CREATE TABLE IF NOT EXISTS saved_properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        property_id TEXT,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS search_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        email TEXT,
        phone TEXT,
        city TEXT NOT NULL,
        max_price REAL,
        min_area REAL,
        min_rooms INTEGER,
        min_discount_pct REAL DEFAULT 10.0,
        channel TEXT DEFAULT 'email',
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. CRM & Lead Sourcing
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id TEXT,
        agent_id INTEGER,
        agency_id INTEGER,
        contact_name TEXT,
        contact_phone TEXT,
        contact_email TEXT,
        status TEXT DEFAULT 'Nowy',
        source TEXT,
        next_contact_date TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS crm_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        agent_id INTEGER,
        note TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
    );
    """)

    # 7. Subscriptions, Payments, Plans
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscription_plans (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        price_monthly REAL NOT NULL,
        features_json TEXT,
        max_agents INTEGER DEFAULT 1,
        trial_days INTEGER DEFAULT 7,
        is_active BOOLEAN DEFAULT 1
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_id INTEGER,
        user_id INTEGER,
        plan_id TEXT,
        status TEXT DEFAULT 'active',
        trial_ends_at DATETIME,
        renews_at DATETIME,
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subscription_id INTEGER,
        amount REAL,
        currency TEXT DEFAULT 'PLN',
        status TEXT,
        stripe_payment_intent TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 8. Partners & Mortgage Leads
    cur.execute("""
    CREATE TABLE IF NOT EXISTS partners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        commission_rate REAL DEFAULT 0.0,
        commission_type TEXT DEFAULT 'fixed',
        is_active BOOLEAN DEFAULT 1
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS mortgage_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partner_id INTEGER,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        city TEXT,
        property_price REAL,
        down_payment REAL,
        loan_period_years INTEGER,
        rodo_consent BOOLEAN DEFAULT 1,
        status TEXT DEFAULT 'Nowy',
        commission_value REAL DEFAULT 0.0,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 9. Service Marketplace
    cur.execute("""
    CREATE TABLE IF NOT EXISTS service_providers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        company_name TEXT NOT NULL,
        contact_phone TEXT,
        contact_email TEXT,
        city TEXT,
        description TEXT,
        rating REAL DEFAULT 5.0,
        is_verified BOOLEAN DEFAULT 1
    );
    """)

    # 10. MLS (Współpraca Międzybiurowa)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS mls_offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id TEXT NOT NULL,
        agency_id INTEGER,
        split_percent REAL DEFAULT 50.0,
        terms TEXT,
        contact_name TEXT,
        contact_phone TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 11. Reports & Promotions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agency_name TEXT,
        agent_name TEXT,
        client_name TEXT,
        properties_json TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS promotions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id TEXT,
        tier TEXT DEFAULT 'premium',
        starts_at DATETIME,
        ends_at DATETIME,
        is_active BOOLEAN DEFAULT 1
    );
    """)

    # 12. Audit Log & Analytics Events
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity TEXT,
        entity_id TEXT,
        details TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS analytics_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        property_id TEXT,
        city TEXT,
        metadata_json TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON analytics_events(event_type);")

    # Seed default plans if empty
    cur.execute("SELECT COUNT(*) FROM subscription_plans;")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO subscription_plans (id, name, price_monthly, max_agents, trial_days, features_json)
        VALUES (?, ?, ?, ?, ?, ?);
        """, [
            ('agent_solo', 'Agent Solo', 99.0, 1, 7, json.dumps(['Baza ofert prywatnych (Leady)', '1 doradca', '1 miasto', 'Podstawowy CRM'])),
            ('biuro_pro', 'Biuro PRO', 249.0, 3, 7, json.dumps(['Nielimitowane leady prywatne', 'Generator Raportów PDF z logo biura', 'Analizator cen i wyceny rynkowe', 'Do 3 stanowisk doradców', 'Giełda MLS 50/50'])),
            ('partner_vip', 'Partner VIP', 499.0, 10, 7, json.dumps(['Wyróżnienie biura na 1. miejscu', 'Całe województwo bez limitów', 'Nielimitowane stanowiska', 'Odznaka Zweryfikowany Partner', 'Dedykowany opiekun'])),
            ('vip_investor', 'VIP Investor Snajper', 89.0, 1, 7, json.dumps(['Snajper Okazji w czasie rzeczywistym', 'Alerty WhatsApp/Email', 'Kalkulator ROI i Flip', 'Dostęp do ofert poniżej rynku']))
        ])

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("SQLite database initialized successfully")
