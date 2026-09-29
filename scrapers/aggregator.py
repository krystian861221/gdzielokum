import difflib
from typing import List, Dict, Any, Optional
from scrapers.otodom_scraper import scrape_otodom
from scrapers.olx_scraper import scrape_olx
from scrapers.agencies_scraper import scrape_all_agencies
from scrapers.nieruchomosci_online_scraper import scrape_nieruchomosci_online

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
    city: str = "jelenia-gora",
    max_total_price: Optional[int] = 2400,
    category: str = "wynajem",
    property_type: str = "Mieszkania",
    sources: Optional[List[str]] = None,
    private_only: bool = False,
    sort_by: str = "Cena: od najniższej"
) -> List[Dict[str, Any]]:
    """
    Pobiera i łączy oferty ze wszystkich wybranych źródeł dla dowolnego typu nieruchomości.
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
        except Exception as e:
            print(f"Błąd agregacji biur i Gratki: {e}")

    # Deduplikacja po ID oraz URL (np. ogłoszenia wyróżnione powtórzone na OLX)
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

    # Filtrowanie cenowe całkowitego kosztu
    filtered = []
    for ad in all_offers:
        tot = ad.get("total_price", 0)
        if isinstance(tot, (int, float)) and tot > 0:
            if max_total_price is None or tot <= max_total_price:
                filtered.append(ad)
        else:
            filtered.append(ad)

    # Oznaczanie potencjalnych duplikatów
    for i in range(len(filtered)):
        for j in range(i + 1, len(filtered)):
            if are_similar_offers(filtered[i], filtered[j]):
                filtered[i]["duplicate_of"] = filtered[j]["source"]
                filtered[j]["duplicate_of"] = filtered[i]["source"]

    # Sortowanie
    if sort_by == "Cena: od najniższej":
        filtered.sort(key=lambda x: x.get("total_price") if isinstance(x.get("total_price"), (int, float)) and x.get("total_price") > 0 else 999999999)
    elif sort_by == "Cena: od najwyższej":
        filtered.sort(key=lambda x: x.get("total_price") if isinstance(x.get("total_price"), (int, float)) else -1, reverse=True)

    return filtered
