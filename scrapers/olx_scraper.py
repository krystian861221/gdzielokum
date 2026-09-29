import re
import json
import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright
from scrapers.polish_cities import normalize_slug

def parse_price(price_str: str) -> int:
    if not price_str:
        return 0
    clean = re.sub(r"[^\d]", "", price_str.split("zł")[0] if "zł" in price_str else price_str)
    try:
        return int(clean)
    except ValueError:
        return 0

async def _scrape_olx_async(
    city: str = "jelenia-gora",
    price_max: Optional[int] = None,
    category: str = "wynajem",
    property_type: str = "mieszkania",
    private_only: bool = False
) -> List[Dict[str, Any]]:
    clean_city = normalize_slug(city)
    
    cat_map = {
        "mieszkania": "mieszkania", "mieszkanie": "mieszkania",
        "domy": "domy", "dom": "domy",
        "dzialki": "dzialki", "dzialka": "dzialki",
        "lokale": "lokale-uzytkowe", "lokal": "lokale-uzytkowe", "lokale-uzytkowe": "lokale-uzytkowe",
        "pokoje": "pokoje", "pokoj": "pokoje"
    }
    olx_prop = cat_map.get(property_type.lower(), "mieszkania")
    trans_type = "wynajem" if category == "wynajem" else "sprzedaz"
    
    urls_to_try = [
        f"https://www.olx.pl/nieruchomosci/{olx_prop}/{trans_type}/{clean_city}/",
        f"https://www.olx.pl/nieruchomosci/{olx_prop}/{trans_type}/q-{clean_city}/"
    ]
    
    params = []
    if price_max:
        params.append(f"search%5Bfilter_float_price%3Ato%5D={price_max}")
    if private_only:
        params.append("search%5Bprivate_business%5D=private")
        
    query_str = ("?" + "&".join(params)) if params else ""

    results = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            for base_url in urls_to_try:
                full_url = base_url + query_str
                try:
                    await page.goto(full_url, timeout=25000)
                    content = await page.content()
                    
                    # 1. Wyciągnij mapę oryginalnych zdjęć z danych JSON-LD
                    photo_map = {}
                    ld_scripts = re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', content, re.DOTALL)
                    for s in ld_scripts:
                        try:
                            s_data = json.loads(s)
                            if isinstance(s_data, dict):
                                offers_obj = s_data.get("offers", {})
                                offers_list = offers_obj.get("offers", []) if isinstance(offers_obj, dict) else []
                                for off in offers_list:
                                    off_url = off.get("url", "")
                                    off_imgs = off.get("image", [])
                                    if off_url and off_imgs:
                                        first_img = off_imgs[0] if isinstance(off_imgs, list) else off_imgs
                                        photo_map[off_url] = first_img
                                        if "-ID" in off_url:
                                            off_id = off_url.split("-ID")[-1].replace(".html", "").split("?")[0]
                                            photo_map[off_id] = first_img
                        except Exception:
                            pass

                    # 2. Przewiń stronę, aby załadować elementy DOM
                    await page.evaluate("""async () => {
                        for (let i = 0; i < 4; i++) {
                            window.scrollBy(0, 1000);
                            await new Promise(r => setTimeout(r, 200));
                        }
                        window.scrollTo(0, 0);
                    }""")
                    await page.wait_for_timeout(800)

                    cards = await page.query_selector_all('[data-cy="l-card"]')
                    if len(cards) > 0:
                        for card in cards:
                            title_el = await card.query_selector('h6') or await card.query_selector('h4')
                            title = (await title_el.inner_text()).strip() if title_el else ""
                            
                            price_el = await card.query_selector('[data-testid="ad-price"]')
                            price_text = (await price_el.inner_text()).strip() if price_el else ""
                            base_price = parse_price(price_text)
                            
                            link_el = await card.query_selector('a')
                            link = await link_el.get_attribute('href') if link_el else ""
                            if link and not link.startswith('http'):
                                link = "https://www.olx.pl" + link
                                
                            clean_link = link.split("?")[0]
                            ad_id = clean_link.split("-ID")[-1].replace(".html", "") if "-ID" in clean_link else ""

                            # Pobierz zdjęcie: najpierw z JSON-LD, potem z DOM
                            img = photo_map.get(clean_link) or photo_map.get(link) or photo_map.get(ad_id)
                            
                            if not img:
                                img_el = await card.query_selector('img')
                                if img_el:
                                    dom_src = await img_el.get_attribute('src')
                                    if not dom_src or not dom_src.startswith('http') or 'no_thumbnail' in dom_src:
                                        dom_srcset = await img_el.get_attribute('srcset')
                                        if dom_srcset:
                                            dom_src = dom_srcset.split(',')[0].strip().split(' ')[0]
                                    if dom_src and dom_src.startswith('http') and 'no_thumbnail' not in dom_src:
                                        img = dom_src
                            
                            loc_el = await card.query_selector('[data-testid="location-date"]')
                            loc_date = (await loc_el.inner_text()).strip() if loc_el else ""
                            
                            parts = loc_date.split(" - ")
                            location = parts[0] if parts else city.capitalize()
                            date_str = parts[1] if len(parts) > 1 else ""
                            
                            if title and base_price > 0:
                                results.append({
                                    "id": f"olx_{ad_id if ad_id else hash(link)}",
                                    "source": "OLX",
                                    "title": title,
                                    "base_price": base_price,
                                    "admin_fee": 0,
                                    "total_price": base_price,
                                    "area": 0,
                                    "rooms": "",
                                    "location": location,
                                    "image": img if img and img.startswith("http") else None,
                                    "url": link,
                                    "is_private": private_only,
                                    "advertiser": "Osoba prywatna" if private_only else "OLX",
                                    "date": date_str
                                })
                        break
                except Exception as inner_e:
                    print(f"Próba {base_url} nie powiodła się: {inner_e}")
                    
            await browser.close()
    except Exception as e:
        print(f"Błąd podczas pobierania OLX dla {city}: {e}")

    return results

def scrape_olx(
    city: str = "jelenia-gora",
    price_max: Optional[int] = None,
    category: str = "wynajem",
    property_type: str = "mieszkania",
    private_only: bool = False
) -> List[Dict[str, Any]]:
    return asyncio.run(_scrape_olx_async(city, price_max, category, property_type, private_only))
