import re
from typing import Dict, Any, Tuple, List
try:
    from scrapers.polish_cities import correct_city_spelling
except Exception:
    try:
        from scrapers.polish_cities import normalize_slug as correct_city_spelling
    except Exception:
        def correct_city_spelling(city_name: str) -> str:
            replacements = {
                'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
                'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
            }
            res = city_name.lower().strip()
            for pol, lat in replacements.items():
                res = res.replace(pol, lat)
            return re.sub(r'[^a-z0-9]+', '-', res).strip('-')

def parse_natural_language_query(query: str) -> Dict[str, Any]:
    """
    Parsuje zapytanie w języku naturalnym użytkownika na parametry filtrów:
    miasto, cena max, metraż min/max, liczba pokoi, balkon, garaż, rynek pierwotny/wtórny, okazja poniżej rynku.
    """
    params = {
        "city": "wroclaw",
        "max_price": None,
        "min_price": None,
        "min_area": None,
        "max_area": None,
        "rooms": None,
        "has_balcony": False,
        "has_garage": False,
        "deals_only": False,
        "extracted_tags": []
    }
    q = query.lower()

    # 1. Wykrywanie miasta
    polish_towns = [
        "wrocław", "wroclaw", "warszawa", "kraków", "krakow", "poznań", "poznan",
        "gdańsk", "gdansk", "łódź", "lodz", "szczecin", "lubin", "legnica",
        "katowice", "bydgoszcz", "lublin", "białystok", "bialystok", "gdynia",
        "częstochowa", "czestochowa", "radom", "toruń", "torun", "sosnowiec",
        "kielce", "gliwice", "olsztyn", "bielsko-biała", "bielsko", "zielona góra",
        "zielona gora", "rybnik", "ruda śląska", "tabor", "opole", "gorzów", "elbląg",
        "płock", "dąbrowa górnicza", "wałbrzych", "walbrzych", "włocławek", "tarnów",
        "chorzów", "koszalin", "kalisz", "legnica", "grudziądz", "jaworzno", "słupsk",
        "jastrzębie-zdrój", "nowy sącz", "jelenia góra", "jelenia gora", "konin"
    ]
    for town in polish_towns:
        # np. we wrocławiu, w jeleniej górze, lubin, warszawa
        town_base = town.split()[0]
        if town in q or town_base[:4] in q:
            resolved_city = correct_city_spelling(town)
            params["city"] = resolved_city
            params["extracted_tags"].append(f"📍 Miasto: {resolved_city.capitalize()}")
            break

    # 2. Wykrywanie ceny (np. "do 650 tys", "do 650 000 zł", "do 500k", "600 tys.")
    price_match = re.search(r'(?:do|max|budżet|poniżej|do kwoty)\s*(\d+(?:[\s.,]\d+)?)\s*(tys|k|tysiące|tysięcy|zł|pln)?', q)
    if not price_match:
        price_match = re.search(r'(\d+)\s*(tys|k|tysiące|tysięcy)\b', q)
        
    if price_match:
        val_str = price_match.group(1).replace(" ", "").replace(",", ".")
        val = float(val_str)
        unit = (price_match.group(2) or "").strip()
        if unit in ["tys", "k", "tysiące", "tysięcy"] or val < 2000:
            price_val = int(val * 1000)
        else:
            price_val = int(val)
        params["max_price"] = price_val
        params["extracted_tags"].append(f"💰 Budżet do: {price_val:,} zł".replace(",", " "))

    # 3. Wykrywanie metrażu (np. "minimum 55 m2", "od 50m", "powyżej 40 m²")
    area_match = re.search(r'(?:min|minimum|od|powyżej|przynajmniej)\s*(\d+(?:[\s.,]\d+)?)\s*(?:m2|m²|metr|metrów)', q)
    if not area_match:
        area_match = re.search(r'(\d+)\s*(?:m2|m²)', q)
    if area_match:
        area_val = float(area_match.group(1).replace(",", "."))
        params["min_area"] = area_val
        params["extracted_tags"].append(f"📐 Min. metraż: {area_val:g} m²")

    # 4. Wykrywanie liczby pokoi (np. "3 pokoje", "2-pokojowe", "kawalerka", "4 pok.")
    if "kawalerka" in q or "1 pok" in q or "jedno pokoj" in q:
        params["rooms"] = 1
        params["extracted_tags"].append("🚪 1 pokój (kawalerka)")
    else:
        rooms_match = re.search(r'(\d+)\s*(?:-|–)?\s*(?:pokoj|pokoje|pokoi|pok\b)', q)
        if rooms_match:
            rooms_val = int(rooms_match.group(1))
            params["rooms"] = rooms_val
            params["extracted_tags"].append(f"🚪 Liczba pokoi: {rooms_val}")

    # 5. Balkon / Garaż / Ogród
    if "balkon" in q or "balkonem" in q:
        params["has_balcony"] = True
        params["extracted_tags"].append("🌿 Balkon")
    if "garaż" in q or "garaz" in q or "parking" in q or "miejsce postojowe" in q:
        params["has_garage"] = True
        params["extracted_tags"].append("🚗 Miejsce parkingowe / Garaż")

    # 6. Okazja poniżej rynku
    if "poniżej" in q or "okazj" in q or "tanie" in q or "rabat" in q:
        params["deals_only"] = True
        params["extracted_tags"].append("🔥 Oferty poniżej ceny rynkowej")

    return params

def explain_ai_matching(offers: List[Dict[str, Any]], parsed_params: Dict[str, Any], market_stats: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """
    Filtruje oferty według parametrów AI oraz generuje precyzyjne wyjaśnienie dopasowania.
    """
    matching_offers = []
    below_market_count = 0

    for o in offers:
        matches = True
        
        # Filtr ceny
        if parsed_params.get("max_price"):
            tot = o.get("total_price")
            if tot and tot > parsed_params["max_price"]:
                matches = False
                
        # Filtr metrażu
        if parsed_params.get("min_area"):
            area = o.get("area")
            if area and area < parsed_params["min_area"]:
                matches = False
                
        # Filtr pokoi
        if parsed_params.get("rooms"):
            rooms_str = str(o.get("rooms", ""))
            try:
                r_num = int(''.join(filter(str.isdigit, rooms_str)))
                if r_num != parsed_params["rooms"]:
                    matches = False
            except Exception:
                pass
                
        # Filtr balkonu
        if parsed_params.get("has_balcony"):
            text = (o.get("title", "") + " " + o.get("description", "")).lower()
            if not o.get("has_balcony") and "balkon" not in text:
                matches = False

        if matches:
            matching_offers.append(o)
            if o.get("diff_pct") and o.get("diff_pct") < 0:
                below_market_count += 1

    total_found = len(offers)
    strict_count = len(matching_offers)
    
    explanation = (
        f"Znalazłem **{total_found}** ofert w lokalizacji {parsed_params['city'].capitalize()}. "
        f"**{strict_count}** spełnia wszystkie Twoje kryteria. "
        f"**{below_market_count}** ma cenę/m² poniżej mediany lokalnego rynku."
    )
    return matching_offers if matching_offers else offers, explanation
