import difflib
from typing import List, Dict, Any, Optional
from scrapers.otodom_scraper import scrape_otodom
from scrapers.olx_scraper import scrape_olx
from scrapers.agencies_scraper import scrape_all_agencies
from scrapers.nieruchomosci_online_scraper import scrape_nieruchomosci_online
from analytics.market_analyzer import analyze_market_prices
from analytics.score_engine import calculate_gdzielokum_score
from db.repository import save_property_record, log_event

def are_similar_offers(ad1: Dict[str, Any], ad2: Dict[str, Any]) -> bool:
    if ad1.get("source") == ad2.get("source"):
        return False
        
    t1 = ad1.get("title", "").lower()
    t2 = ad2.get("title", "").lower()
    
    ratio = difflib.SequenceMatcher(None, t1, t2).ratio()
    if ratio > 0.75:
        return True
        
    p1 = ad1.get("base_price")
    p2 = ad2.get("base_price")
    if p1 and p2 and isinstance(p1, (int, float)) and isinstance(p2, (int, float)):
        if abs(p1 - p2) < 50 and ratio > 0.45:
            return True
            
    return False

def aggregate_offers(
    city: str = "wroclaw",
    max_total_price: Optional[int] = None,
    min_total_price: Optional[int] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    rooms: Optional[int] = None,
    category: str = "sprzedaz",
    property_type: str = "Mieszkania",
    sources: Optional[List[str]] = None,
    private_only: bool = False,
    sort_by: str = "GdzieLokum SCORE (Rekomendowane)",
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Pobiera, deduplikuje, ocenia i łączy oferty ze wszystkich wybranych źródeł dla dowolnego typu nieruchomości.
    Zapisuje wyniki do bazy danych SQLite oraz rejestruje zdarzenia analityczne.
    """
    if sources is None:
        sources = ["Otodom", "OLX", "Nieruchomości-online", "Gratka / Biura"]

    all_offers = []

    # 1. Otodom
    if "Otodom" in sources:
        try:
            otodom_ads = scrape_otodom(
                city=city,
                price_max=max_total_price,
                category=category,
                property_type=property_type,
                private_only=private_only
            )
            all_offers.extend(otodom_ads)
        except Exception as e:
            print(f"Błąd agregacji Otodom: {e}")

    # 2. OLX
    if "OLX" in sources:
        try:
            olx_ads = scrape_olx(
                city=city,
                price_max=max_total_price,
                category=category,
                property_type=property_type,
                private_only=private_only
            )
            all_offers.extend(olx_ads)
        except Exception as e:
            print(f"Błąd agregacji OLX: {e}")

    # 3. Nieruchomości-online
    if "Nieruchomości-online" in sources and not private_only:
        try:
            no_ads = scrape_nieruchomosci_online(
                city=city,
                price_max=max_total_price,
                category=category,
                property_type=property_type
            )
            all_offers.extend(no_ads)
        except Exception as e:
            print(f"Błąd agregacji Nieruchomości-online: {e}")

    # 4. Gratka / Morizon (Biura Nieruchomości)
    if ("Gratka / Biura" in sources or "Biura Nieruchomości" in sources) and not private_only:
        try:
            agency_ads = scrape_all_agencies(
                city=city,
                category=category,
                property_type=property_type,
                max_price=max_total_price
            )
            all_offers.extend(agency_ads)
        except Exception as e:
            print(f"Błąd agregacji biur i Gratki: {e}")

    # Deduplikacja po ID oraz URL
    seen_ids = set()
    seen_urls = set()
    unique_offers = []
    for ad in all_offers:
        aid = ad.get("id")
        aurl = ad.get("url")
        if aid and aid in seen_ids:
            continue
        if aurl and aurl in seen_urls:
            continue
        if aid:
            seen_ids.add(aid)
        if aurl:
            seen_urls.add(aurl)
        unique_offers.append(ad)
    all_offers = unique_offers

    # Filtrowanie cenowe i metrażowe
    filtered = []
    for ad in all_offers:
        tot = ad.get("total_price", 0)
        area = ad.get("area", 0)
        
        # Filtr min cena
        if min_total_price and tot and tot < min_total_price:
            continue
        # Filtr max cena
        if max_total_price and tot and tot > max_total_price:
            continue
        # Filtr min metraż
        if min_area and area and area < min_area:
            continue
        # Filtr max metraż
        if max_area and area and area > max_area:
            continue
            
        filtered.append(ad)

    # Obliczenie statystyk rynkowych (mediana m2, średnia m2)
    market_stats = analyze_market_prices(filtered)

    # Obliczenie GdzieLokum SCORE (0-100) dla każdej nieruchomości i zapis do bazy
    for ad in filtered:
        ad["city"] = city
        score_res = calculate_gdzielokum_score(ad, market_stats)
        ad["score"] = score_res["score"]
        ad["score_label"] = score_res["label"]
        ad["score_color"] = score_res["color"]
        ad["score_badge_bg"] = score_res["badge_bg"]
        ad["score_details"] = score_res["sub_scores"]
        
        # Zapisz w relacyjnej bazie SQLite w tle
        try:
            save_property_record(ad)
        except Exception:
            pass

    # Loguj wyszukiwanie do analityki
    try:
        log_event("search", city=city, metadata={"count": len(filtered), "sort": sort_by})
    except Exception:
        pass

    # Sortowanie
    if sort_by == "GdzieLokum SCORE (Rekomendowane)":
        filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
    elif sort_by == "Cena: od najniższej":
        filtered.sort(key=lambda x: x.get("total_price") if isinstance(x.get("total_price"), (int, float)) and x.get("total_price") > 0 else 999999999)
    elif sort_by == "Cena: od najwyższej":
        filtered.sort(key=lambda x: x.get("total_price") if isinstance(x.get("total_price"), (int, float)) else -1, reverse=True)
    elif sort_by == "Cena za m²: od najniższej":
        filtered.sort(key=lambda x: x.get("price_per_m2") if isinstance(x.get("price_per_m2"), (int, float)) and x.get("price_per_m2") > 0 else 999999999)
    elif sort_by == "Cena za m²: od najwyższej":
        filtered.sort(key=lambda x: x.get("price_per_m2") if isinstance(x.get("price_per_m2"), (int, float)) else -1, reverse=True)

    return filtered
