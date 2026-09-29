import requests
import re
import html
from typing import List, Dict, Any, Optional
from scrapers.polish_cities import normalize_slug

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
}

def scrape_nieruchomosci_online(
    city: str = "jelenia-gora",
    price_max: Optional[int] = 2400,
    category: str = "wynajem",
    property_type: str = "mieszkanie"
) -> List[Dict[str, Any]]:
    """
    Pobiera oferty z nieruchomości-online.pl dla mieszkania, domy, działki, lokale itp.
    """
    clean_city = normalize_slug(city)
    cat_param = "wynajem" if category == "wynajem" else "sprzedaz"
    
    # Mapowanie typu
    cat_map = {
        "mieszkania": "mieszkanie", "mieszkanie": "mieszkanie",
        "domy": "dom", "dom": "dom",
        "dzialki": "dzialka", "dzialka": "dzialka",
        "lokale": "lokal-uzytkowy", "lokal": "lokal-uzytkowy", "lokale-uzytkowe": "lokal-uzytkowy",
        "pokoje": "pokoj", "pokoj": "pokoj"
    }
    no_prop = cat_map.get(property_type.lower(), "mieszkanie")
    
    url = f"https://www.nieruchomosci-online.pl/szukaj.html?3,{no_prop},{cat_param},,{clean_city}"
    if price_max:
        url += f"&cena_do={price_max}"

    offers = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            text = html.unescape(r.text)
            tiles = re.findall(r'(<div[^>]*class="tile tile-tile[^"]*"[^>]*>.*?)(?=<div[^>]*class="tile tile-tile|$)', text, re.DOTALL)
            seen_links = set()
            for t in tiles:
                link_m = re.search(r'href="(https://[^\"]+nieruchomosci-online\.pl/[^\"]+\.html)"', t)
                if not link_m:
                    continue
                link = link_m.group(1)
                if link in seen_links:
                    continue
                seen_links.add(link)
                
                title_m = re.search(r'<h2[^>]*>(.*?)</h2>', t, re.DOTALL)
                title = re.sub(r'<[^>]+>', ' ', title_m.group(1)).strip() if title_m else "Nieruchomość"
                
                price_m = re.search(r'(\d[\d\s]{2,})\s*z[łl]', t)
                price = int(re.sub(r'[^\d]', '', price_m.group(1))) if price_m else 0
                
                area_m = re.search(r'(\d+(?:,\d+)?)\s*m[²2]', t)
                area = float(area_m.group(1).replace(',', '.')) if area_m else 0
                
                rooms_m = re.search(r'Liczba pokoi:\s*(\d+)', t)
                rooms = f"{rooms_m.group(1)} pokoje" if rooms_m else ""
                
                img_m = re.search(r'src="(https://i\.st-nieruchomosci-online\.pl/[^"]+)"', t) or re.search(r'data-src="(https://i\.st-nieruchomosci-online\.pl/[^"]+)"', t)
                img = img_m.group(1) if img_m else None
                
                loc_m = re.search(r'<p[^>]*class="[^"]*location[^"]*"[^>]*>(.*?)</p>', t, re.DOTALL)
                loc = re.sub(r'<[^>]+>', ' ', loc_m.group(1)).strip() if loc_m else city.capitalize()
                
                if (price_max is None or price <= price_max) and price > 0:
                    offers.append({
                        "id": f"no_{link.split('/')[-1].replace('.html', '')}",
                        "source": "Nieruchomości-online",
                        "title": title,
                        "base_price": price,
                        "admin_fee": 0,
                        "total_price": price,
                        "area": area,
                        "rooms": rooms,
                        "location": loc,
                        "image": img,
                        "url": link,
                        "is_private": False,
                        "advertiser": "Nieruchomości-online",
                        "date": "Aktualne"
                    })
    except Exception as e:
        print(f"Błąd NO dla {city}: {e}")
        
    return offers
