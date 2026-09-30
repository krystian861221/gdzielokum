import requests
import json
import re
from typing import List, Dict, Any, Optional
from scrapers.polish_cities import normalize_slug, get_otodom_path, VOIVODESHIPS

def scrape_otodom(
    city: str = "jelenia-gora",
    price_max: Optional[int] = None,
    category: str = "wynajem",
    property_type: str = "mieszkanie",
    rooms: Optional[str] = None,
    private_only: bool = False,
    distance_radius: int = 0,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Pobiera ogłoszenia z Otodom dla dowolnego typu nieruchomości (mieszkanie, dom, dzialka, lokal, pokoj).
    """
    clean_city = normalize_slug(city)
    location_path = get_otodom_path(city)
    
    # Mapowanie typu nieruchomości dla Otodom
    cat_map = {
        "mieszkania": "mieszkanie", "mieszkanie": "mieszkanie",
        "domy": "dom", "dom": "dom",
        "dzialki": "dzialka", "dzialka": "dzialka",
        "lokale": "lokal", "lokal": "lokal", "lokale-uzytkowe": "lokal",
        "pokoje": "pokoj", "pokoj": "pokoj"
    }
    oto_prop = cat_map.get(property_type.lower(), "mieszkanie")
    trans_type = "wynajem" if category == "wynajem" else "sprzedaz"
    
    params = {"limit": 36}
    if distance_radius and int(distance_radius) > 0:
        params["distanceRadius"] = int(distance_radius)
    if price_max:
        params["priceMax"] = price_max
    if private_only:
        params["by"] = "USER"
    if rooms and oto_prop == "mieszkanie":
        params["roomsNumber"] = f"[{rooms}]"

    if "cala-polska" in location_path:
        url = f"https://www.otodom.pl/pl/wyniki/{trans_type}/{oto_prop}/cala-polska"
        params["searchingCriteria"] = city
    else:
        url = f"https://www.otodom.pl/pl/wyniki/{trans_type}/{oto_prop}/{location_path}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    results = []
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=12)
        
        if resp.status_code == 404:
            fallback_params = dict(params)
            fallback_params["searchingCriteria"] = city
            fallback_url = f"https://www.otodom.pl/pl/wyniki/{trans_type}/{oto_prop}/cala-polska"
            resp = requests.get(fallback_url, params=fallback_params, headers=headers, timeout=10)

        if resp.status_code == 200:
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text)
            if match:
                data = json.loads(match.group(1))
                page_props = data.get("props", {}).get("pageProps", {})
                search_data = page_props.get("data", {})
                items = search_data.get("searchAds", {}).get("items", [])
                
                if not items and "searchingCriteria" not in params:
                    fallback_params = dict(params)
                    fallback_params["searchingCriteria"] = city
                    fallback_url = f"https://www.otodom.pl/pl/wyniki/{trans_type}/{oto_prop}/cala-polska"
                    f_resp = requests.get(fallback_url, params=fallback_params, headers=headers, timeout=10)
                    if f_resp.status_code == 200:
                        f_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', f_resp.text)
                        if f_match:
                            f_data = json.loads(f_match.group(1))
                            items = f_data.get("props", {}).get("pageProps", {}).get("data", {}).get("searchAds", {}).get("items", [])
                
                for item in items:
                    title = item.get("title", "")
                    slug = item.get("slug", "")
                    direct_url = f"https://www.otodom.pl/pl/oferta/{slug}" if slug else ""
                    
                    base_price = 0
                    total_price_obj = item.get("totalPrice", {})
                    if total_price_obj and isinstance(total_price_obj, dict):
                        base_price = total_price_obj.get("value") or 0
                    
                    rent_obj = item.get("rentPrice", {})
                    admin_fee = 0
                    if rent_obj and isinstance(rent_obj, dict):
                        admin_fee = rent_obj.get("value") or 0
                    
                    total_monthly = base_price + admin_fee if (admin_fee and trans_type == "wynajem") else base_price

                    area = item.get("areaInSquareMeters", 0)
                    rooms_num = item.get("roomsNumber", "")
                    rooms_display = {
                        "ONE": "1 pokój",
                        "TWO": "2 pokoje",
                        "THREE": "3 pokoje",
                        "FOUR": "4 pokoje",
                        "FIVE": "5 pokoi"
                    }.get(rooms_num, str(rooms_num) if rooms_num else "")

                    images = item.get("images", [])
                    image_url = images[0].get("medium") if images else None

                    loc = item.get("location", {})
                    address = loc.get("address", {})
                    street = address.get("street", {}).get("name") if address.get("street") else None
                    subdistrict = address.get("subdistrict", {}).get("name") if address.get("subdistrict") else None
                    district = address.get("district", {}).get("name") if address.get("district") else None
                    city_name = address.get("city", {}).get("name") if address.get("city") else city
                    
                    loc_parts = [p for p in [street, subdistrict, district, city_name] if p]
                    location_str = ", ".join(loc_parts) if loc_parts else city.capitalize()

                    agency = item.get("agency", {})
                    is_private = True if not agency else False
                    agency_name = agency.get("name") if agency else "Osoba prywatna"

                    results.append({
                        "id": f"otodom_{item.get('id', slug)}",
                        "source": "Otodom",
                        "title": title,
                        "base_price": base_price,
                        "admin_fee": admin_fee,
                        "total_price": total_monthly,
                        "area": area,
                        "rooms": rooms_display,
                        "location": location_str,
                        "image": image_url,
                        "url": direct_url,
                        "is_private": is_private,
                        "advertiser": agency_name,
                        "date": item.get("dateCreated", "")
                    })
    except Exception as e:
        print(f"Błąd podczas pobierania Otodom dla {city}: {e}")

    return results
