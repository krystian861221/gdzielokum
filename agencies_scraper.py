import os
import json
import re
import requests
from typing import List, Dict, Any, Optional
from scrapers.polish_cities import normalize_slug

AGENCIES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "local_agencies.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
}

def load_local_agencies(city: str = "jelenia-gora") -> List[Dict[str, Any]]:
    clean_city = normalize_slug(city)
    if os.path.exists(AGENCIES_FILE):
        try:
            with open(AGENCIES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(clean_city, [])
        except Exception as e:
            print(f"Błąd odczytu bazy agencji: {e}")
    return []

def save_custom_agency(city: str, agency: Dict[str, Any]) -> bool:
    clean_city = normalize_slug(city)
    data = {}
    if os.path.exists(AGENCIES_FILE):
        try:
            with open(AGENCIES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    
    city_agencies = data.get(clean_city, [])
    if not any(a.get("website") == agency.get("website") for a in city_agencies):
        city_agencies.append(agency)
        data[clean_city] = city_agencies
        with open(AGENCIES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    return False

def scrape_stepien_agency(category: str = "wynajem", property_type: str = "mieszkania", max_price: Optional[int] = None) -> List[Dict[str, Any]]:
    offers = []
    prop = "mieszkania" if "mieszkan" in property_type else ("domy" if "dom" in property_type else ("dzialki" if "dzial" in property_type else "lokale"))
    trans = "wynajem" if category == "wynajem" else "sprzedaz"
    url = f"https://stepien.nieruchomosci.pl/oferty/{prop}/{trans}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        boxes = re.findall(r'<div[^>]*class="[^"]*offer-box[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', r.text, re.DOTALL)
        for b in boxes:
            link_m = re.search(r'href=["\']([^"\']+)["\']', b)
            title_m = re.search(r'<h3[^>]*>(.*?)</h3>', b, re.DOTALL)
            loc_m = re.search(r'<h4[^>]*>(.*?)</h4>', b, re.DOTALL)
            price_m = re.search(r'(\d[\d\s]{2,})\s*(?:z[łl]|PLN)', b, re.I)
            img_m = re.search(r'data-src=["\']([^"\']+)["\']', b) or re.search(r'src=["\']([^"\']+)["\']', b)

            link = link_m.group(1).lstrip('/') if link_m else ""
            if link and not link.startswith('http'):
                link = f"https://stepien.nieruchomosci.pl/{link}"

            title = re.sub(r'<[^>]+>', ' ', title_m.group(1)).strip() if title_m else "Nieruchomość"
            location = re.sub(r'<[^>]+>', ' ', loc_m.group(1)).strip() if loc_m else "Jelenia Góra"
            price = int(re.sub(r'[^\d]', '', price_m.group(1))) if price_m else 0
            img = img_m.group(1) if img_m else None
            if img and not img.startswith('http'):
                img = f"https://stepien.nieruchomosci.pl/{img.lstrip('/')}"
            if img and ("transparent" in img or "blank" in img):
                img = None

            if (max_price is None or price <= max_price) and price > 0:
                offers.append({
                    "id": f"stepien_{hash(link)}",
                    "source": "Gratka / Biura",
                    "title": f"{title} ({location})",
                    "base_price": price,
                    "admin_fee": 0,
                    "total_price": price,
                    "area": 0,
                    "rooms": "",
                    "location": f"Jelenia Góra, {location}",
                    "image": img,
                    "url": link,
                    "is_private": False,
                    "advertiser": "Stępień Nieruchomości",
                    "date": "Oferta biura"
                })
    except Exception as e:
        print(f"Błąd Stępień scraper: {e}")
    return offers

def scrape_morizon_agencies(city: str = "jelenia-gora", category: str = "wynajem", property_type: str = "mieszkania", max_price: Optional[int] = None) -> List[Dict[str, Any]]:
    offers = []
    clean_city = normalize_slug(city)
    
    # Mapowanie typu
    cat_map = {
        "mieszkania": "mieszkania", "mieszkanie": "mieszkania",
        "domy": "domy", "dom": "domy",
        "dzialki": "dzialki", "dzialka": "dzialki",
        "lokale": "lokale", "lokal": "lokale", "lokale-uzytkowe": "lokale",
        "pokoje": "pokoje", "pokoj": "pokoje"
    }
    mor_prop = cat_map.get(property_type.lower(), "mieszkania")
    
    if category == "wynajem":
        url = f"https://www.morizon.pl/do-wynajecia/{mor_prop}/{clean_city}/"
    else:
        url = f"https://www.morizon.pl/{mor_prop}/{clean_city}/"
        
    if max_price:
        url += f"?ps%5Bprice_to%5D={max_price}"
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        all_imgs = [m for m in re.findall(r'(https://img\d*\.staticmorizon\.com\.pl/[^"\']+)', r.text) if '3x2_' in m or 'thumb' in m]
        
        matches = re.finditer(r'<a[^>]+href="(/oferta/[^"]+)"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        seen = set()
        idx = 0
        for m in matches:
            href = m.group(1)
            if href in seen:
                continue
            seen.add(href)
            
            pos = m.start()
            window = r.text[max(0, pos-200):min(len(r.text), pos+1400)]
            price_m = re.search(r'(\d[\d\s]{2,})\s*(?:z[łl]|PLN)', window, re.I)
            price = int(re.sub(r'[^\d]', '', price_m.group(1))) if price_m else 0
            
            img = all_imgs[idx] if idx < len(all_imgs) else None
            idx += 1
            
            slug_parts = href.split('/')[-1].split('-')
            area = 0
            for part in slug_parts:
                if part.endswith('m2') and part[:-2].isdigit():
                    area = int(part[:-2])
                    break
                    
            clean_title = " ".join([p.capitalize() for p in slug_parts if not p.startswith('mzn') and not p.endswith('m2')])
            if not clean_title:
                clean_title = f"{property_type.capitalize()} na {category}"
                
            if (max_price is None or price <= max_price) and price > 0:
                offers.append({
                    "id": f"agency_morizon_{hash(href)}",
                    "source": "Gratka / Biura",
                    "title": clean_title,
                    "base_price": price,
                    "admin_fee": 0,
                    "total_price": price,
                    "area": area,
                    "rooms": "",
                    "location": f"{city.capitalize()}",
                    "image": img,
                    "url": f"https://www.morizon.pl{href}",
                    "is_private": False,
                    "advertiser": "Biuro Nieruchomości (Morizon)",
                    "date": "Aktualne w agencji"
                })
    except Exception as e:
        print(f"Błąd Morizon scraper: {e}")
        
    return offers

def scrape_all_agencies(city: str = "jelenia-gora", category: str = "wynajem", property_type: str = "mieszkania", max_price: Optional[int] = None) -> List[Dict[str, Any]]:
    agency_offers = []
    
    morizon_ads = scrape_morizon_agencies(city=city, category=category, property_type=property_type, max_price=max_price)
    agency_offers.extend(morizon_ads)

    clean = normalize_slug(city)
    if any(k in clean for k in ["jelenia", "cieplic", "kowary", "piechowic", "karkonos"]):
        stepien_ads = scrape_stepien_agency(category=category, property_type=property_type, max_price=max_price)
        agency_offers.extend(stepien_ads)
        
    return agency_offers

def discover_agencies_for_city(city: str) -> List[Dict[str, Any]]:
    discovered = []
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        query = f"biuro nieruchomości {city} oferty wynajem sprzedaz"
        results = list(ddgs.text(query, max_results=6))
        for res in results:
            url = res.get("href", "")
            title = res.get("title", "")
            snippet = res.get("body", "")
            
            if any(dom in url for dom in ["olx.pl", "otodom.pl", "morizon.pl", "gratka.pl", "nieruchomosci-online.pl", "allegro.pl", "facebook.com", "trovit.pl"]):
                continue
                
            match = re.search(r"https?://(?:www\.)?([^/]+)", url)
            if match:
                domain = match.group(1)
                discovered.append({
                    "name": title.split("-")[0].split("|")[0].strip(),
                    "website": f"https://{domain}",
                    "rentals_url": url,
                    "phone": "Sprawdź na stronie",
                    "address": city.capitalize(),
                    "snippet": snippet
                })
    except Exception as e:
        print(f"Błąd podczas wyszukiwania biur w DuckDuckGo dla {city}: {e}")
        
    return discovered
